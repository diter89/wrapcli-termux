#!/usr/bin/env python3
import os
from pathlib import Path

class Config:

    DEFAULT_API_MODEL = "accounts/fireworks/models/gpt-oss-120b"
    API_BASE_URL = "https://api.fireworks.ai/inference/v1/chat/completions"
    API_TIMEOUT = 120
    
    AI_CONFIG = {
        "max_tokens": 16000,
        "top_p": 1,
        "top_k": 40,
        "presence_penalty": 0,
        "frequency_penalty": 0,
        "temperature": 0.6
    }
    
    # Shell Configuration
    MAX_SHELL_CONTEXT = 10  # Maximum number of shell commands to keep in context
    MAX_CONVERSATION_HISTORY = 20  # Maximum conversation history to keep
    CONTEXT_FOR_AI = 5  # Number of recent commands to send to AI
    
    # Interactive Commands 
    INTERACTIVE_COMMANDS = {
        'nano', 'vim', 'vi', 'emacs', 'mc', 'htop', 'top', 
        'fzf', 'less', 'more', 'man', 'tmux', 'screen',
        'python3', 'python', 'node', 'irb', 'psql', 'mysql',
        'nvim', 'nu', 'xonsh', 'apt', 'sudo',
        'sqlite3', 'redis-cli', 'mongo', 'bash', 'zsh', 'fish'
    }
    
    # Syntax Highlighting Extensions
    SYNTAX_EXTENSIONS = {
        '.py': 'python',
        '.js': 'javascript', 
        '.json': 'json',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.sh': 'bash',
        '.bash': 'bash',
        '.zsh': 'zsh',
        '.fish': 'fish',
        '.sql': 'sql',
        '.html': 'html',
        '.css': 'css',
        '.xml': 'xml',
        '.md': 'markdown',
        '.txt': 'text'
    }
    
    # Commands that should trigger syntax highlighting
    SYNTAX_HIGHLIGHT_COMMANDS = ['cat', 'head', 'tail', 'batcat', 'bat']
    
    LS_COMMANDS = ['ls', 'la', 'lsd', 'll']
    
    # File type icons and colors
    FILE_ICONS = {
        'directory': '📁',
        'file': '📄', 
        'executable': '⚙️',
        'symlink': '🔗',
        'image': '🖼️',
        'video': '🎬',
        'audio': '🎵',
        'archive': '📦',
        'document': '📝',
        'code': '💻'
    }
    
    FILE_COLORS = {
        'directory': 'bold blue',
        'file': 'white',
        'executable': 'bold green', 
        'symlink': 'cyan',
        'image': 'magenta',
        'video': 'red',
        'audio': 'yellow',
        'archive': 'bold yellow',
        'document': 'blue',
        'code': 'green',
        'hidden': 'dim white'
    }
    
    # File extensions mapping
    FILE_EXTENSIONS = {
        # Images
        '.jpg': 'image', '.jpeg': 'image', '.png': 'image', '.gif': 'image', 
        '.bmp': 'image', '.svg': 'image', '.webp': 'image', '.ico': 'image',
        
        # Videos  
        '.mp4': 'video', '.avi': 'video', '.mkv': 'video', '.mov': 'video',
        '.wmv': 'video', '.flv': 'video', '.webm': 'video', '.m4v': 'video',
        
        # Audio
        '.mp3': 'audio', '.wav': 'audio', '.flac': 'audio', '.aac': 'audio',
        '.ogg': 'audio', '.m4a': 'audio', '.wma': 'audio',
        
        # Archives
        '.zip': 'archive', '.rar': 'archive', '.7z': 'archive', '.tar': 'archive',
        '.gz': 'archive', '.bz2': 'archive', '.xz': 'archive', '.deb': 'archive',
        '.rpm': 'archive', '.dmg': 'archive',
        
        # Documents
        '.pdf': 'document', '.doc': 'document', '.docx': 'document', '.xls': 'document',
        '.xlsx': 'document', '.ppt': 'document', '.pptx': 'document', '.txt': 'document',
        '.rtf': 'document', '.odt': 'document', '.ods': 'document', '.odp': 'document',
        
        # Code files
        '.py': 'code', '.js': 'code', '.html': 'code', '.css': 'code', '.java': 'code',
        '.cpp': 'code', '.c': 'code', '.h': 'code', '.php': 'code', '.rb': 'code',
        '.go': 'code', '.rs': 'code', '.swift': 'code', '.kt': 'code', '.scala': 'code',
        '.sh': 'code', '.bash': 'code', '.zsh': 'code', '.fish': 'code', '.json': 'code',
        '.xml': 'code', '.yaml': 'code', '.yml': 'code', '.toml': 'code', '.ini': 'code',
        '.cfg': 'code', '.conf': 'code', '.sql': 'code', '.r': 'code', '.m': 'code'
    }
    
    # UI Configuration
    REFRESH_RATE = 10  # Rich Live refresh rate per second
    
    # Directories
    CONFIG_DIR = Path.home() / '.wrapcli_awokwokw'
    LOG_FILE = CONFIG_DIR / 'shell.log'
    HISTORY_FILE = CONFIG_DIR / 'history.json'
    
    # Prompts and Messages
    WELCOME_MESSAGE = """🚀 [bold]Hybrid Shell[/bold] Started!
Press [cyan]Alt+H[/cyan] for help, [red]Ctrl+C[/red] to exit
Context-aware AI + Shell integration with [bold green]Proper Rich Live Streaming[/bold green]
[dim]Interactive commands (nano, mc, fzf, etc.) now supported![/dim]"""
    
    HELP_KEYBINDS = [
        ("Alt+A", "Switch to AI mode"),
        ("Alt+S", "Switch to Shell mode"), 
        ("Alt+H", "Show this help"),
        ("Alt+C", "Clear context & conversation"),
        ("Ctrl+C", "Exit application")
    ]
    
    HELP_SPECIAL_COMMANDS = [
        ("clear", "AI", "Clear conversation history"),
        ("context", "AI", "Show current shell context"),
        ("exit", "Both", "Exit the shell")
    ]
    
    # Styling
    PROMPT_STYLES = {
        'ai_mode': '#00aa00 bold',
        'shell_mode': '#0066cc bold', 
        'separator': '#666666',
        'path': '#ffaa00',
        'prompt': '#ffffff bold'
    }
    
    @classmethod
    def ensure_directories(cls):
        cls.CONFIG_DIR.mkdir(exist_ok=True)
    
    @classmethod
    def get_api_key(cls):
        return os.getenv("FIREWORKS_API_KEY")
    
    @classmethod
    def get_model_name(cls):
        return os.getenv("FIREWORKS_MODEL", cls.DEFAULT_API_MODEL)
