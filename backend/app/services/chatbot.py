import os
import json
import re
from typing import Dict, Any, List, Optional
import cohere
from app.mcp.tools import add_task, list_tasks, complete_task, delete_task, update_task, get_current_user
from app.models.conversation import ConversationRepository
from app.models.message import MessageRepository
from app.api.models.chat import ToolCallInfo


class ChatbotService:
    """Service class for handling AI chatbot interactions with Cohere and MCP tools."""

    def __init__(self):
        """Initialize the chatbot service with Cohere client and tools."""
        """Initialize the chatbot service with Cohere client and tools."""
        from app.core.config import settings
        api_key = settings.COHERE_API_KEY
        
        # Initialize Cohere client if key exists
        if api_key:
            try:
                self.co = cohere.Client(api_key)
                print("Cohere client initialized successfully")
            except Exception as e:
                print(f"Error initializing Cohere client: {e}")
                self.co = None
        else:
            self.co = None
            print("WARNING: COHERE_API_KEY not found in settings. Chatbot will not function.")
        self.conversation_repo = ConversationRepository()
        self.message_repo = MessageRepository()

        # Register available tools
        self.tools = {
            "add_task": add_task,
            "list_tasks": list_tasks,
            "complete_task": complete_task,
            "delete_task": delete_task,
            "update_task": update_task,
            "get_current_user": get_current_user
        }

        # System prompt for the chatbot
        self.system_prompt = """
        You are "The Evolution AI", a versatile and clever task management assistant.
        Your goal is to help {user_name} ({user_email}) manage their todo list with high efficiency.
        
        ### MULTILINGUAL CAPABILITIES:
        - You understand and can respond in **English**, **Roman Urdu/Hindi** (e.g., "Mera task add kardo"), and **Urdu** (e.g., "میرا کام شامل کریں").
        - If the user talks in Roman Urdu, you should respond in Roman Urdu.
        - If the user asks you to talk in Urdu ("Urdu mein baat karo"), switch to Urdu script.
        
        ### CORE TOOLS:
        - add_task: Create a new task (params: title, description)
        - list_tasks: Search and show tasks (params: status, search). 
          *When listing, show them in a clean numbered or bullet list with their IDs if available.*
        - complete_task: Mark a task as done (params: task_id)
        - delete_task: Permanently remove a task (params: task_id)
        - update_task: Modify an existing task (params: task_id, title, description, status)
        - get_current_user: Retrieve detailed profile info
        
        ### OPERATIONAL RULES:
        1. When {user_name} asks to perform an action (add, mark complete, delete, etc.), call the tool IMMEDIATELY.
        2. Format tool calls as a single JSON block:
           ```json
           {{"tool": "tool_name", "params": {{"key": "value"}}}}
           ```
        3. For "delete kardo" or "baqi tasks khatam kardo", use `delete_task` with the correct ID.
        4. If you don't have the task ID, ask the user for it or list the tasks first.
        5. After tool execution, a confirmation will be shown.
        6. For "marks bhi lagado" or "complete kardo", use `complete_task`.
        7. For "list dikhao" or "show my tasks", use `list_tasks`.
        """

    async def _get_user_info(self, db, user_id: str) -> Dict[str, str]:
        """Fetch user info for personification."""
        try:
            from app.models.user import User
            from sqlmodel import select
            statement = select(User).where(User.id == user_id)
            result = await db.execute(statement)
            user = result.scalars().first()
            if user:
                return {"name": user.name, "email": user.email}
        except Exception:
            pass
        return {"name": "User", "email": "Unknown"}

    async def process_message_with_db(
        self,
        db,
        user_id: str,
        message: str,
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a user message with database access and return an appropriate response.
        """
        # Get user info for personification
        user_info = await self._get_user_info(db, user_id)
        
        # Format system prompt with user data
        personalized_prompt = self.system_prompt.format(
            user_name=user_info["name"],
            user_email=user_info["email"]
        )

        # Get or create conversation
        if conversation_id:
            conversation = await self.conversation_repo.get_by_id(
                db=db,
                conversation_id=conversation_id,
                user_id=user_id
            )
            if not conversation:
                conversation = await self.conversation_repo.create(db=db, user_id=user_id)
                conversation_id = conversation.id
        else:
            conversation = await self.conversation_repo.create(db=db, user_id=user_id)
            conversation_id = conversation.id

        # Add user message to conversation
        await self.message_repo.create(
            db=db,
            conversation_id=conversation_id,
            role="user",
            content=message
        )

        # Process the request
        result = await self.process_multi_step_request(
            db=db,
            user_id=user_id,
            message=message,
            conversation_id=conversation_id,
            personalized_prompt=personalized_prompt
        )

        # Update conversation timestamp
        await self.conversation_repo.update_timestamp(db=db, conversation_id=conversation_id)

        return result

    def _generate_tool_response(self, tool_calls_executed: List[Dict[str, Any]], user_language: str = "ur") -> str:
        """Generate a natural confirmation message based on tool results."""
        if not tool_calls_executed:
            return "Main samajh nahi paya, kya aap phir se bol sakte hain?" if user_language == "ur" else "I couldn't understand that. Could you repeat?"

        # Templates for responses
        templates = {
            "ur": { # Roman Urdu
                "add_task": "✓ Task add ho gaya hai!",
                "complete_task": "✓ Task complete ho gaya hai!",
                "delete_task": "✓ Task delete kar diya gaya hai!",
                "update_task": "✓ Task update ho gaya hai!",
                "list_tasks": "Yeh rahe aapke tasks:",
                "get_current_user": "Aapki profile information yeh hai:"
            },
            "en": {
                "add_task": "✓ Task added successfully!",
                "complete_task": "✓ Task marked as complete!",
                "delete_task": "✓ Task deleted successfully!",
                "update_task": "✓ Task updated successfully!",
                "list_tasks": "Here are your tasks:",
                "get_current_user": "Here is your profile information:"
            }
        }

        lang = "ur" if user_language == "ur" else "en"
        msgs = []

        for call in tool_calls_executed:
            tool = call["tool"]
            result = call["result"]
            
            if "error" in result:
                error_msg = result["error"]
                if lang == "ur":
                    msgs.append(f"❌ Error: {error_msg}")
                else:
                    msgs.append(f"❌ Error: {error_msg}")
                continue

            # Special handling for list_tasks
            if tool == "list_tasks":
                tasks = result.get("tasks", [])
                if not tasks:
                    msgs.append("Aapki list abhi khali hai." if lang == "ur" else "Your list is empty.")
                else:
                    msgs.append(templates[lang]["list_tasks"])
                    for i, t in enumerate(tasks):
                        status_char = "✅" if t.get("completed") else "⏳"
                        msgs.append(f"{i+1}. [{t.get('id')}] {status_char} {t.get('title')}")
            
            # Special handling for get_current_user
            elif tool == "get_current_user":
                msgs.append(templates[lang]["get_current_user"])
                msgs.append(f"Name: {result.get('name')}\nEmail: {result.get('email')}")
            
            # Default templates
            else:
                msgs.append(templates[lang].get(tool, "Done!"))

        return "\n".join(msgs)

    async def _process_tool_calls(
        self,
        db,
        user_id: str,
        response_text: str,
        conversation_id: str
    ) -> List[Dict[str, Any]]:
        """Extract and execute tool calls from text."""
        tool_calls_executed = []
        
        # Robust pattern to catch JSON blocks
        pattern = r'```json\s*\n?({.*?})\s*\n?```'
        matches = re.findall(pattern, response_text, re.DOTALL)

        for match in matches:
            try:
                data = json.loads(match)
                tool_name = data.get("tool")
                params = data.get("params", {})

                if tool_name in self.tools:
                    tool_func = self.tools[tool_name]
                    
                    try:
                        # Clean params
                        params.pop("user_id", None)
                        
                        # IMPORTANT: Convert task_id to int if present, as tools expect int
                        if "task_id" in params:
                            try:
                                params["task_id"] = int(params["task_id"])
                            except (ValueError, TypeError):
                                pass

                        # Tool execution
                        if tool_name == "get_current_user":
                            result = await tool_func(user_id, db)
                        else:
                            result = await tool_func(user_id=user_id, db=db, **params)
                    except Exception as e:
                        error_detail = f"Error: {str(e)}"
                        print(f"Tool Execution Error: {error_detail}")
                        result = {"error": error_detail}

                    tool_calls_executed.append({
                        "tool": tool_name,
                        "params": params,
                        "result": result
                    })

                    # Log execution as a system message
                    await self.message_repo.create(
                        db=db,
                        conversation_id=conversation_id,
                        role="assistant",
                        content=f"[System: Executed {tool_name}. Result: {result}]"
                    )
            except Exception as e:
                print(f"JSON Parsing/Unexpected Error: {e}")
                continue
                
        return tool_calls_executed

    async def process_multi_step_request(
        self,
        db,
        user_id: str,
        message: str,
        conversation_id: str,
        personalized_prompt: str,
        max_iterations: int = 5
    ) -> Dict[str, Any]:
        """
        Handle multi-step tool execution.
        """
        if not self.co:
            return {
                "conversation_id": conversation_id,
                "response": "Cohere API key missing. Please check backend .env",
                "tool_calls": []
            }

        iteration = 0
        all_tool_calls = []
        current_input = message

        while iteration < max_iterations:
            iteration += 1
            
            # Fetch history for context
            db_messages = await self.message_repo.get_conversation_messages(
                db=db,
                conversation_id=conversation_id
            )
            chat_history = [
                {"role": "USER" if m.role == "user" else "CHATBOT", "message": m.content}
                for m in db_messages
            ]

            # Call AI
            response = self.co.chat(
                message=current_input,
                chat_history=chat_history[:-1], # Keep context but exclude current
                preamble=personalized_prompt
            )

            # Check for tool calls
            executed = await self._process_tool_calls(db, user_id, response.text, conversation_id)
            
            if executed:
                all_tool_calls.extend(executed)
                
                # OPTIMIZATION: Instead of calling AI again, generate an immediate confirmation
                # This makes the response ~2x faster.
                final_text = self._generate_tool_response(executed, user_language="ur")
                
                # Save final response to DB
                await self.message_repo.create(
                    db=db,
                    conversation_id=conversation_id,
                    role="assistant",
                    content=final_text
                )
                
                return {
                    "conversation_id": conversation_id,
                    "response": final_text,
                    "tool_calls": all_tool_calls
                }
            else:
                # No more tools, this is the final natural response
                # Save it to DB
                await self.message_repo.create(
                    db=db,
                    conversation_id=conversation_id,
                    role="assistant",
                    content=response.text
                )
                return {
                    "conversation_id": conversation_id,
                    "response": response.text,
                    "tool_calls": all_tool_calls
                }

        return {
            "conversation_id": conversation_id,
            "response": "I'm sorry, that took too many steps. Can we try something simpler?",
            "tool_calls": all_tool_calls
        }