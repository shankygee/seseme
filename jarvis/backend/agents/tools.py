"""
Jarvis Tools - Capabilities for the AI Agent

These tools define what actions Jarvis can take on behalf of the user.
Each tool has a name, description, input schema, and execution handler.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Callable
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Result from a tool execution."""
    success: bool
    data: Any
    error: str | None = None


# ============== Tool Definitions for Claude API ==============

JARVIS_TOOLS = [
    {
        "name": "get_current_time",
        "description": "Get the current date and time in the user's timezone",
        "input_schema": {
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": "Timezone (e.g., 'America/New_York', 'Europe/London'). Defaults to UTC.",
                }
            },
            "required": [],
        },
    },
    {
        "name": "set_reminder",
        "description": "Set a reminder for the user at a specific time. The reminder will be delivered as a notification.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The reminder message",
                },
                "time": {
                    "type": "string",
                    "description": "When to remind. ISO 8601 format (e.g., '2024-03-15T14:30:00') or relative (e.g., 'in 30 minutes', 'tomorrow at 9am')",
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "normal", "high"],
                    "description": "Priority level of the reminder",
                },
            },
            "required": ["message", "time"],
        },
    },
    {
        "name": "search_web",
        "description": "Search the web for information. Use this to find current information, news, or answer factual questions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query",
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results to return (1-10)",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "send_message",
        "description": "Send a text message or email to a contact",
        "input_schema": {
            "type": "object",
            "properties": {
                "recipient": {
                    "type": "string",
                    "description": "Name, phone number, or email of the recipient",
                },
                "message": {
                    "type": "string",
                    "description": "The message content",
                },
                "method": {
                    "type": "string",
                    "enum": ["sms", "email", "imessage"],
                    "description": "How to send the message",
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject (required for email)",
                },
            },
            "required": ["recipient", "message", "method"],
        },
    },
    {
        "name": "get_weather",
        "description": "Get current weather and forecast for a location",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name or 'current' for user's location",
                },
                "days": {
                    "type": "integer",
                    "description": "Number of forecast days (1-7)",
                    "default": 1,
                },
            },
            "required": ["location"],
        },
    },
    {
        "name": "manage_calendar",
        "description": "View, create, or modify calendar events",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["view", "create", "update", "delete"],
                    "description": "What to do with the calendar",
                },
                "date": {
                    "type": "string",
                    "description": "Date for viewing or creating events (YYYY-MM-DD or 'today', 'tomorrow')",
                },
                "title": {
                    "type": "string",
                    "description": "Event title (for create/update)",
                },
                "start_time": {
                    "type": "string",
                    "description": "Event start time (HH:MM)",
                },
                "end_time": {
                    "type": "string",
                    "description": "Event end time (HH:MM)",
                },
                "event_id": {
                    "type": "string",
                    "description": "Event ID (for update/delete)",
                },
            },
            "required": ["action"],
        },
    },
    {
        "name": "control_smart_home",
        "description": "Control smart home devices (lights, thermostat, locks, etc.)",
        "input_schema": {
            "type": "object",
            "properties": {
                "device_type": {
                    "type": "string",
                    "enum": ["lights", "thermostat", "lock", "blinds", "tv", "speaker"],
                    "description": "Type of device to control",
                },
                "device_name": {
                    "type": "string",
                    "description": "Specific device name or room (e.g., 'living room lights', 'bedroom thermostat')",
                },
                "action": {
                    "type": "string",
                    "description": "Action to perform (e.g., 'on', 'off', 'set to 72', 'dim to 50%')",
                },
            },
            "required": ["device_type", "action"],
        },
    },
    {
        "name": "take_note",
        "description": "Create a note or add to existing notes",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Note title",
                },
                "content": {
                    "type": "string",
                    "description": "Note content",
                },
                "folder": {
                    "type": "string",
                    "description": "Folder to save the note in",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags for organizing the note",
                },
            },
            "required": ["content"],
        },
    },
    {
        "name": "play_music",
        "description": "Control music playback - play, pause, skip, or search for music",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["play", "pause", "skip", "previous", "search", "volume"],
                    "description": "Music control action",
                },
                "query": {
                    "type": "string",
                    "description": "Song, artist, album, or playlist name (for play/search)",
                },
                "volume": {
                    "type": "integer",
                    "description": "Volume level 0-100 (for volume action)",
                },
            },
            "required": ["action"],
        },
    },
    {
        "name": "get_news",
        "description": "Get latest news headlines, optionally filtered by topic",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "News topic (e.g., 'technology', 'sports', 'business'). Leave empty for top headlines.",
                },
                "count": {
                    "type": "integer",
                    "description": "Number of articles (1-10)",
                    "default": 5,
                },
            },
            "required": [],
        },
    },
    {
        "name": "calculate",
        "description": "Perform mathematical calculations, unit conversions, or currency exchange",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Math expression or conversion (e.g., '15% of 200', '100 USD to EUR', '5 miles to km')",
                },
            },
            "required": ["expression"],
        },
    },
    {
        "name": "manage_tasks",
        "description": "Manage to-do list - add, complete, or view tasks",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["add", "complete", "list", "delete"],
                    "description": "Task action",
                },
                "task": {
                    "type": "string",
                    "description": "Task description (for add)",
                },
                "task_id": {
                    "type": "string",
                    "description": "Task ID (for complete/delete)",
                },
                "due_date": {
                    "type": "string",
                    "description": "Due date (for add)",
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                    "description": "Task priority",
                },
            },
            "required": ["action"],
        },
    },
]


# ============== Tool Execution Handlers ==============

class ToolExecutor:
    """Executes tools and returns results."""

    def __init__(self):
        self._reminders: list[dict] = []
        self._notes: list[dict] = []
        self._tasks: list[dict] = []
        self._http_client = httpx.AsyncClient()

    async def execute(self, tool_name: str, tool_input: dict) -> ToolResult:
        """
        Execute a tool by name with given input.

        Args:
            tool_name: Name of the tool to execute
            tool_input: Input parameters for the tool

        Returns:
            ToolResult with success status and data
        """
        handler = getattr(self, f"_execute_{tool_name}", None)
        if handler is None:
            return ToolResult(
                success=False,
                data=None,
                error=f"Unknown tool: {tool_name}",
            )

        try:
            result = await handler(tool_input)
            return ToolResult(success=True, data=result)
        except Exception as e:
            logger.error(f"Tool execution error: {tool_name}: {e}")
            return ToolResult(success=False, data=None, error=str(e))

    async def _execute_get_current_time(self, input: dict) -> dict:
        """Get current time."""
        from zoneinfo import ZoneInfo

        tz_name = input.get("timezone", "UTC")
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            tz = ZoneInfo("UTC")

        now = datetime.now(tz)
        return {
            "datetime": now.isoformat(),
            "date": now.strftime("%A, %B %d, %Y"),
            "time": now.strftime("%I:%M %p"),
            "timezone": tz_name,
        }

    async def _execute_set_reminder(self, input: dict) -> dict:
        """Set a reminder."""
        reminder = {
            "id": f"rem_{len(self._reminders) + 1}",
            "message": input["message"],
            "time": input["time"],
            "priority": input.get("priority", "normal"),
            "created_at": datetime.utcnow().isoformat(),
            "status": "pending",
        }
        self._reminders.append(reminder)

        return {
            "status": "created",
            "reminder_id": reminder["id"],
            "message": f"Reminder set: '{input['message']}' for {input['time']}",
        }

    async def _execute_search_web(self, input: dict) -> dict:
        """Search the web (mock implementation - integrate with real search API)."""
        query = input["query"]
        num_results = min(input.get("num_results", 5), 10)

        # In production, integrate with a real search API like:
        # - Brave Search API
        # - Google Custom Search
        # - Bing Search API

        return {
            "query": query,
            "message": f"Web search for '{query}' would return {num_results} results. Integrate with a search API for real results.",
            "results": [],
            "note": "Integrate with Brave Search, Google, or Bing API for production",
        }

    async def _execute_send_message(self, input: dict) -> dict:
        """Send a message (mock - integrate with real messaging services)."""
        return {
            "status": "queued",
            "recipient": input["recipient"],
            "method": input["method"],
            "message": f"Message to {input['recipient']} via {input['method']} has been queued.",
            "note": "Integrate with Twilio (SMS), SendGrid (email), or Apple Push for production",
        }

    async def _execute_get_weather(self, input: dict) -> dict:
        """Get weather (mock - integrate with weather API)."""
        location = input["location"]

        # In production, integrate with:
        # - OpenWeatherMap API
        # - WeatherAPI
        # - AccuWeather

        return {
            "location": location,
            "message": f"Weather for {location} would be fetched here.",
            "note": "Integrate with OpenWeatherMap or WeatherAPI for production",
        }

    async def _execute_manage_calendar(self, input: dict) -> dict:
        """Manage calendar (mock - integrate with calendar services)."""
        action = input["action"]

        # In production, integrate with:
        # - Google Calendar API
        # - Apple Calendar (via EventKit on iOS)
        # - Microsoft Graph (Outlook)

        return {
            "action": action,
            "message": f"Calendar {action} action would be performed here.",
            "note": "Integrate with Google Calendar, Apple EventKit, or Microsoft Graph",
        }

    async def _execute_control_smart_home(self, input: dict) -> dict:
        """Control smart home (mock - integrate with smart home APIs)."""
        device_type = input["device_type"]
        action = input["action"]
        device_name = input.get("device_name", device_type)

        # In production, integrate with:
        # - HomeKit (Apple)
        # - SmartThings
        # - Google Home
        # - Philips Hue (lights)
        # - Nest (thermostat)

        return {
            "device": device_name,
            "action": action,
            "status": "executed",
            "message": f"{device_name} - {action}",
            "note": "Integrate with HomeKit, SmartThings, or device-specific APIs",
        }

    async def _execute_take_note(self, input: dict) -> dict:
        """Create a note."""
        note = {
            "id": f"note_{len(self._notes) + 1}",
            "title": input.get("title", "Untitled"),
            "content": input["content"],
            "folder": input.get("folder", "General"),
            "tags": input.get("tags", []),
            "created_at": datetime.utcnow().isoformat(),
        }
        self._notes.append(note)

        return {
            "status": "created",
            "note_id": note["id"],
            "title": note["title"],
            "message": f"Note '{note['title']}' created successfully.",
        }

    async def _execute_play_music(self, input: dict) -> dict:
        """Control music (mock - integrate with music services)."""
        action = input["action"]
        query = input.get("query", "")

        # In production, integrate with:
        # - Apple Music
        # - Spotify
        # - Local media player

        return {
            "action": action,
            "query": query,
            "status": "executed",
            "message": f"Music {action}" + (f": {query}" if query else ""),
            "note": "Integrate with Spotify, Apple Music, or local player",
        }

    async def _execute_get_news(self, input: dict) -> dict:
        """Get news (mock - integrate with news API)."""
        topic = input.get("topic", "top headlines")

        # In production, integrate with:
        # - NewsAPI
        # - Google News
        # - Apple News

        return {
            "topic": topic,
            "message": f"News about '{topic}' would be fetched here.",
            "note": "Integrate with NewsAPI or similar service",
        }

    async def _execute_calculate(self, input: dict) -> dict:
        """Perform calculations."""
        expression = input["expression"]

        # Simple evaluation - in production, use a proper math parser
        try:
            # Handle simple math expressions
            # WARNING: eval is dangerous - use a safe math parser in production
            safe_expr = expression.replace("^", "**")
            result = eval(safe_expr, {"__builtins__": {}}, {})
            return {
                "expression": expression,
                "result": result,
            }
        except Exception:
            return {
                "expression": expression,
                "message": "Complex calculation - integrate with a math API or parser",
                "note": "Use sympy or a safe expression parser for production",
            }

    async def _execute_manage_tasks(self, input: dict) -> dict:
        """Manage tasks."""
        action = input["action"]

        if action == "add":
            task = {
                "id": f"task_{len(self._tasks) + 1}",
                "description": input["task"],
                "due_date": input.get("due_date"),
                "priority": input.get("priority", "medium"),
                "status": "pending",
                "created_at": datetime.utcnow().isoformat(),
            }
            self._tasks.append(task)
            return {
                "status": "created",
                "task_id": task["id"],
                "message": f"Task added: {input['task']}",
            }

        elif action == "list":
            pending_tasks = [t for t in self._tasks if t["status"] == "pending"]
            return {
                "tasks": pending_tasks,
                "count": len(pending_tasks),
            }

        elif action == "complete":
            task_id = input.get("task_id")
            for task in self._tasks:
                if task["id"] == task_id:
                    task["status"] = "completed"
                    return {"status": "completed", "task_id": task_id}
            return {"status": "not_found", "task_id": task_id}

        elif action == "delete":
            task_id = input.get("task_id")
            self._tasks = [t for t in self._tasks if t["id"] != task_id]
            return {"status": "deleted", "task_id": task_id}

        return {"error": f"Unknown action: {action}"}


# Global executor instance
tool_executor = ToolExecutor()
