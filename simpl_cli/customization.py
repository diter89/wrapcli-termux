#!/usr/bin/env python3
import os
import json
import re
import time
from datetime import datetime
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import (
        Progress,
        SpinnerColumn,
        TextColumn,
        TimeElapsedColumn, 
        BarColumn,
        TaskProgressColumn,
        MofNCompleteColumn
        )
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.status import Status
from rich.console import Group
from rich.live import Live
from rich.align import Align

from .config import Config
from .environment import get_prompt_env_indicators, get_status_info, get_all_env_info

class UIManager:
    def __init__(self, console: Console):
        self.console = console
    
    def get_prompt_text(self, mode: str):
        prompt_parts = []
        
        if mode == "ai":
            prompt_parts.append(('class:ai_mode', '🤖 AI'))
        else:
            prompt_parts.append(('class:shell_mode', '💻 SHELL'))
        
        env_indicators = get_prompt_env_indicators()
        if env_indicators:
            prompt_parts.append(('class:separator', '│'))
            prompt_parts.extend(env_indicators)
        
        prompt_parts.extend([
            ('class:separator', '│'),
            ('class:path', f'{os.getcwd()}'),
            ('class:prompt', ' ~❯ ')
        ])
        
        return FormattedText(prompt_parts)
    
    def get_style(self):
        environment_styles = {
            'env_python': 'fg:#3776ab bold',      # Python blue
            'env_git': 'fg:#f05033 bold',         # Git orange-red  
            'env_node': 'fg:#68a063 bold',        # Node green
            'env_docker': 'fg:#2496ed bold',      # Docker blue
            'env_system': 'fg:#ffd700 bold',      # System gold
        }
        
        combined_styles = {**Config.PROMPT_STYLES, **environment_styles}
        return Style.from_dict(combined_styles)
    
    def show_welcome(self):
        env_info = get_all_env_info()
        
        welcome_parts = [Config.WELCOME_MESSAGE]
        
        env_summary = []
        if env_info.get('python'):
            py_env = env_info['python']
            env_summary.append(f"🐍 Python: {py_env['display']} (v{py_env['python_version']})")
        
        if env_info.get('git'):
            git_info = env_info['git']
            status_indicator = "●" if git_info.get('has_changes') else "○"
            env_summary.append(f"📊 Git: {git_info['branch']} {status_indicator}")
        
        if env_info.get('node'):
            node_info = env_info['node']
            env_summary.append(f"📦 Node: {node_info['name']} (v{node_info['version']})")
        
        if env_info.get('docker'):
            docker_info = env_info['docker']
            env_summary.append(f"🐳 Docker: {docker_info['display']}")
        
        if env_summary:
            welcome_parts.append("\n\n🔍 Detected Environments:")
            welcome_parts.extend([f"  {item}" for item in env_summary])
        
        welcome_text = "\n".join(welcome_parts)
        
        welcome_panel = Panel.fit(
            welcome_text,
            border_style="blue"
        )
        self.console.print(welcome_panel)
        self.console.print()
    
    def show_help(self):
        help_table = Table(title="🚀 Hybrid Shell Commands", show_header=True, header_style="bold blue")
        help_table.add_column("Keybind", style="cyan", no_wrap=True)
        help_table.add_column("Description", style="white")
        
        for keybind, description in Config.HELP_KEYBINDS:
            help_table.add_row(keybind, description)
        
        help_table.add_row("Alt+Z", "Resume cancelled AI stream")
        
        special_table = Table(title="Special Commands", show_header=True, header_style="bold green")
        special_table.add_column("Command", style="cyan", no_wrap=True)
        special_table.add_column("Mode", style="yellow", no_wrap=True)
        special_table.add_column("Description", style="white")
        
        for command, mode, description in Config.HELP_SPECIAL_COMMANDS:
            special_table.add_row(command, mode, description)
        
        special_table.add_row("resume", "AI", "Resume cancelled AI response")
        special_table.add_row("cancelstate", "AI", "Show cancelled stream details")
        
        env_table = Table(title="Environment Commands", show_header=True, header_style="bold magenta")
        env_table.add_column("Command", style="cyan", no_wrap=True)
        env_table.add_column("Description", style="white")
        
        env_commands = [
            ("!env", "Show current environment status"),
            ("!status", "Show detailed system and environment info"),
            ("!git", "Show git repository information"),
            ("!python", "Show Python environment details")
        ]
        
        for command, description in env_commands:
            env_table.add_row(command, description)
        
        self.console.print("")
        self.console.print(Panel(help_table, title="[bold]Keybindings[/bold]", border_style="blue"))
        self.console.print(Panel(special_table, title="[bold]Commands[/bold]", border_style="green"))
        self.console.print(Panel(env_table, title="[bold]Environment[/bold]", border_style="magenta"))
        self.console.print("")

    def show_environment_status(self):
        env_info = get_all_env_info()
        
        env_table = Table(title="🔍 Environment Status", show_header=True, header_style="bold cyan")
        env_table.add_column("Type", style="yellow", no_wrap=True, width=12)
        env_table.add_column("Status", style="green", width=20)
        env_table.add_column("Details", style="white")
        
        if env_info.get('python'):
            py_env = env_info['python']
            env_table.add_row(
                "🐍 Python",
                py_env['display'],
                f"Version: {py_env['python_version']} | Type: {py_env['type']}"
            )
        else:
            env_table.add_row("🐍 Python", "[dim]No virtual env[/dim]", f"System Python {'.'.join(map(str, __import__('sys').version_info[:3]))}")
        
        if env_info.get('git'):
            git_info = env_info['git']
            status_text = "Clean" if not git_info.get('has_changes') else "Modified"
            ahead_behind = ""
            if git_info.get('ahead', 0) > 0:
                ahead_behind += f" ↑{git_info['ahead']}"
            if git_info.get('behind', 0) > 0:
                ahead_behind += f" ↓{git_info['behind']}"
            
            env_table.add_row(
                "📊 Git",
                f"Branch: {git_info['branch']}",
                f"Status: {status_text}{ahead_behind}"
            )
        else:
            env_table.add_row("📊 Git", "[dim]Not a git repo[/dim]", "-")
        
        if env_info.get('node'):
            node_info = env_info['node']
            modules_status = "✅ Installed" if node_info.get('has_modules') else "❌ Missing"
            env_table.add_row(
                "📦 Node.js",
                node_info['name'],
                f"Version: {node_info['version']} | Modules: {modules_status}"
            )
        else:
            env_table.add_row("📦 Node.js", "[dim]No package.json[/dim]", "-")
        
        if env_info.get('docker'):
            docker_info = env_info['docker']
            docker_details = []
            if docker_info.get('has_dockerfile'):
                docker_details.append("Dockerfile")
            if docker_info.get('has_compose'):
                docker_details.append("docker-compose.yml")
            if docker_info.get('inside_container'):
                docker_details.append("Inside container")
            
            env_table.add_row(
                "🐳 Docker",
                docker_info['display'],
                " | ".join(docker_details) if docker_details else "Detected"
            )
        else:
            env_table.add_row("🐳 Docker", "[dim]Not detected[/dim]", "-")
        
        system_info = env_info.get('system', {})
        cpu_percent = system_info.get('cpu_percent', 0)
        mem_percent = system_info.get('memory_percent', 0)
        uptime = system_info.get('uptime', 'Unknown')
        
        cpu_style = "red" if cpu_percent > 80 else "yellow" if cpu_percent > 60 else "green"
        mem_style = "red" if mem_percent > 85 else "yellow" if mem_percent > 70 else "green"
        
        env_table.add_row(
            "💻 System",
            f"Running • {uptime}",
            f"CPU: [{cpu_style}]{cpu_percent:.1f}%[/{cpu_style}] | MEM: [{mem_style}]{mem_percent:.1f}%[/{mem_style}]"
        )
        
        self.console.print("")
        self.console.print(Panel(env_table, border_style="cyan"))
        self.console.print("")
    
    def show_mode_switch(self, mode_name: str):
        pass
    
    def show_context_cleared(self):
        self.console.print(Panel("🧹 Context and conversation cleared!", title="[green]Cleared[/green]", border_style="green"))
    
    def show_conversation_cleared(self):
        self.console.print(Panel("🧹 Conversation history cleared", title="[green]Cleared[/green]", border_style="green"))
    
    def show_context_table(self, shell_context: list):
        if not shell_context:
            self.console.print(Panel(
                "[yellow]No shell context available[/yellow]",
                title="Shell Context",
                border_style="yellow"
            ))
            return
            
        context_table = Table(title="Shell Context", show_header=True, header_style="bold cyan")
        context_table.add_column("Time", style="dim", no_wrap=True)
        context_table.add_column("Command", style="cyan")
        context_table.add_column("Directory", style="yellow", no_wrap=True)
        context_table.add_column("Output Preview", style="white")
        
        for entry in shell_context[-Config.CONTEXT_FOR_AI:]:
            output_preview = entry['output'][:50] + "..." if len(entry['output']) > 50 else entry['output']
            output_preview = output_preview.replace('\n', ' ')
            
            context_table.add_row(
                entry['timestamp'],
                entry['command'],
                entry['cwd'].split('/')[-1],
                output_preview
            )
            
        self.console.print(Panel(context_table, border_style="cyan"))
    
    def display_shell_output(self, command: str, result):
        base_cmd = command.strip().split()[0]
        if self._should_use_ls_table(command, base_cmd):
            self._display_ls_table(command, result)
            return
            
        output = result.stdout + result.stderr
        
        if result.stdout and result.stderr:
            combined_output = Text()
            if result.stdout:
                combined_output.append(result.stdout, style="white")
            if result.stderr:
                combined_output.append(result.stderr, style="red")
            
            self.console.print(Panel(
                combined_output,
                title=f"💻 Shell: {command}",
                border_style="blue"
            ))
        elif result.stdout:
            syntax_content = self._try_syntax_highlighting(command, result.stdout)
            self.console.print(Panel(
                syntax_content,
                title=f"💻 Shell: {command}",
                border_style="blue"
            ))
        elif result.stderr:
            self.console.print(Panel(
                f"[red]{result.stderr}[/red]",
                title=f"💻 Shell: {command}",
                border_style="red"
            ))
        else:
            self.console.print(Panel(
                "[dim]No output[/dim]",
                title=f"💻 Shell: {command}",
                border_style="blue"
            ))
    
    def _should_use_ls_table(self, command: str, base_cmd: str) -> bool:
        if base_cmd in Config.LS_COMMANDS:
            return True
            
        if base_cmd == 'ls' or command.startswith('ls '):
            return True
            
        return False
    
    def _display_ls_table(self, command: str, result):
        if result.returncode != 0:
            self.console.print(Panel(
                f"[red]{result.stderr}[/red]",
                title=f"💻 Shell: {command}",
                border_style="red"
            ))
            return
            
        if not result.stdout.strip():
            self.console.print(Panel(
                "[yellow]Directory is empty[/yellow]",
                title=f"📁 Directory Listing: {command}",
                border_style="blue"
            ))
            return
        
        try:
            ls_table = self._create_ls_table(command, result.stdout)
            self.console.print(Panel(
                ls_table,
                title=f"📁 Directory Listing: {command}",
                border_style="blue",
                padding=(1, 2)
            ))
        except Exception as e:
            self.console.print(Panel(
                result.stdout,
                title=f"💻 Shell: {command}",
                border_style="blue"
            ))
    
    def _create_ls_table(self, command: str, ls_output: str) -> Table:
        # Create table
        table = Table(show_header=True, header_style="bold cyan", box=None)
        
        lines = ls_output.strip().split('\n')
        has_details = self._is_detailed_listing(lines, command)
        
        if has_details:
            # Detailed listing (ls -l style)
            table.add_column("Permissions", style="dim")
            table.add_column("Links", style="dim", justify="right")
            table.add_column("Owner", style="dim")
            table.add_column("Group", style="dim") 
            table.add_column("Size", style="cyan", justify="right")
            table.add_column("Date", style="yellow")
            table.add_column("Name", style="bold")
        else:
            # Simple listing
            table.add_column("Type", justify="center", width=4)
            table.add_column("Name", style="bold")
            table.add_column("Size", style="cyan", justify="right")
            table.add_column("Modified", style="yellow")
        
        target_dir = self._extract_target_directory(command)
        for line in lines:
            line = line.strip()
            if not line or line.startswith('total '):
                continue
                
            try:
                if has_details:
                    self._add_detailed_row(table, line, target_dir)
                else:
                    self._add_simple_row(table, line, target_dir)
            except Exception as e:
                continue
        
        return table
    
    def _is_detailed_listing(self, lines: list, command: str) -> bool:
        if '-l' in command:
            return True
            
        detailed_patterns = 0
        for line in lines[:5]:
            line = line.strip()
            if not line or line.startswith('total'):
                continue
                
            parts = line.split()
            if len(parts) >= 8:
                first_part = parts[0]
                if (len(first_part) == 10 and 
                    first_part[0] in '-dlbcsp' and 
                    all(c in 'rwx-' for c in first_part[1:])):
                    detailed_patterns += 1
        
        non_empty_lines = len([l for l in lines if l.strip() and not l.startswith('total')])
        return detailed_patterns > 0 and (detailed_patterns / max(non_empty_lines, 1)) > 0.5
    
    def _extract_target_directory(self, command: str) -> str:
        parts = command.split()
        for part in parts[1:]:
            if not part.startswith('-'):
                if os.path.isabs(part):
                    return part
                else:
                    return os.path.join(os.getcwd(), part)
        
        return os.getcwd()
    
    def _add_detailed_row(self, table: Table, line: str, current_dir: str):
        parts = line.split()
        if len(parts) < 8:
            return
            
        permissions = parts[0]
        links = parts[1] 
        owner = parts[2]
        group = parts[3]
        size = parts[4]
        
        if len(parts) >= 9:
            date_parts = parts[5:8]
            name = ' '.join(parts[8:])
        else:
            date_parts = parts[5:7]
            name = ' '.join(parts[7:])
            
        date_str = ' '.join(date_parts)
        
        file_type, icon, color = self._get_file_info(name, current_dir, permissions)
        
        formatted_size = self._format_size(size) if size.isdigit() else size
        
        table.add_row(
            f"[dim]{permissions}[/dim]",
            f"[dim]{links}[/dim]",
            f"[dim]{owner}[/dim]", 
            f"[dim]{group}[/dim]",
            f"[cyan]{formatted_size}[/cyan]",
            f"[yellow]{date_str}[/yellow]",
            f"[{color}]{icon} {name}[/{color}]"
        )
    
    def _add_simple_row(self, table: Table, filename: str, current_dir: str):
        try:
            file_path = os.path.join(current_dir, filename)
            file_type, icon, color = self._get_file_info(filename, current_dir)
            
            size = "-"
            mtime = "?"
            
            try:
                if os.path.exists(file_path):
                    stat_info = os.stat(file_path)
                    if not os.path.isdir(file_path):
                        size = self._format_size(stat_info.st_size)
                    else:
                        size = "-"
                    mtime = datetime.fromtimestamp(stat_info.st_mtime).strftime("%b %d %H:%M")
                else:
                    if os.getcwd() == current_dir:
                        stat_info = os.stat(filename)
                        if not os.path.isdir(filename):
                            size = self._format_size(stat_info.st_size)
                        mtime = datetime.fromtimestamp(stat_info.st_mtime).strftime("%b %d %H:%M")
                    
            except (OSError, PermissionError, FileNotFoundError):
                size = "?"
                mtime = "?"
            
            table.add_row(
                f"[{color}]{icon}[/{color}]",
                f"[{color}]{filename}[/{color}]",
                f"[cyan]{size}[/cyan]",
                f"[yellow]{mtime}[/yellow]"
            )
            
        except Exception as e:
            file_type, icon, color = self._get_file_info(filename, current_dir)
            table.add_row(
                f"[{color}]{icon}[/{color}]",
                f"[{color}]{filename}[/{color}]",
                "[dim]?[/dim]",
                "[dim]?[/dim]"
            )
    
    def _get_file_info(self, filename: str, current_dir: str, permissions: str = None):
        file_path = os.path.join(current_dir, filename)
        
        is_hidden = filename.startswith('.')
        
        try:
            if permissions:
                if permissions.startswith('d'):
                    file_type = 'directory'
                elif permissions.startswith('l'):
                    file_type = 'symlink'  
                elif 'x' in permissions:
                    file_type = 'executable'
                else:
                    file_type = self._get_file_type_by_extension(filename)
            elif os.path.exists(file_path):
                if os.path.isdir(file_path):
                    file_type = 'directory'
                elif os.path.islink(file_path):
                    file_type = 'symlink'
                elif os.access(file_path, os.X_OK) and not os.path.isdir(file_path):
                    file_type = 'executable'
                else:
                    file_type = self._get_file_type_by_extension(filename)
            else:
                alt_path = os.path.join(os.getcwd(), filename)
                if current_dir != os.getcwd() and os.path.exists(alt_path):
                    if os.path.isdir(alt_path):
                        file_type = 'directory'
                    elif os.path.islink(alt_path):
                        file_type = 'symlink'
                    elif os.access(alt_path, os.X_OK):
                        file_type = 'executable'
                    else:
                        file_type = self._get_file_type_by_extension(filename)
                else:
                    file_type = self._get_file_type_by_extension(filename)
                
        except (OSError, PermissionError):
            file_type = self._get_file_type_by_extension(filename)
        
        icon = Config.FILE_ICONS.get(file_type, Config.FILE_ICONS['file'])
        color = Config.FILE_COLORS.get('hidden' if is_hidden else file_type, Config.FILE_COLORS['file'])
        
        return file_type, icon, color
    
    def _get_file_type_by_extension(self, filename: str) -> str:
        if not filename or filename.startswith('.') and '.' not in filename[1:]:
            return 'file'
            
        ext = '.' + filename.split('.')[-1].lower() if '.' in filename else ''
        return Config.FILE_EXTENSIONS.get(ext, 'file')
    
    def _format_size(self, size_bytes) -> str:
        try:
            size_bytes = int(size_bytes)
        except (ValueError, TypeError):
            return str(size_bytes)
            
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        if i == 0:
            return f"{size_bytes} {size_names[i]}"
        else:
            return f"{size_bytes:.1f} {size_names[i]}"
    
    def _try_syntax_highlighting(self, command: str, output: str):
        base_cmd = command.split()[0]
        if base_cmd not in Config.SYNTAX_HIGHLIGHT_COMMANDS:
            return output
        
        for ext, lang in Config.SYNTAX_EXTENSIONS.items():
            if ext in command:
                try:
                    return Syntax(output, lang, theme="github-dark", line_numbers=True, indent_guides=True)
                except:
                    break
        
        return output
    
    def display_directory_change(self, command: str, new_dir: str):
        output = f"Changed directory to: {new_dir}"
        self.console.print(Panel(
            f"[green]{output}[/green]",
            title=f"💻 Shell: {command}",
            border_style="blue",
            highlight=True,
        ))
    
    def display_error(self, command: str, error_msg: str):
        self.console.print(Panel(
            f"[red]{error_msg}[/red]",
            title=f"💻 Shell: {command}",
            border_style="red"
        ))
    
    def display_interactive_start(self, command: str):
        self.console.print(f"🎮 [yellow]Starting interactive mode: {command}[/yellow]")
        self.console.print("[dim]Use Ctrl+C or app's exit command to return to shell[/dim]")
    
    def display_interactive_end(self, command: str, return_code: int):
        if return_code == 0:
            self.console.print(f"✅ [green]{command} completed successfully[/green]")
        else:
            self.console.print(f"⚠️ [yellow]{command} exited with code: {return_code}[/yellow]")
    
    def display_interrupt(self, message: str = "^C - Command interrupted"):
        self.console.print(Panel(
            f"[yellow]{message}[/yellow]",
            title="💻 Shell",
            border_style="yellow"
        ))
    
    def display_goodbye(self):
        self.console.print("\n👋 [yellow]Goodbye![/yellow]")
    
    def create_status(self, message: str):
        return Status(f"[bold green]{message}", console=self.console)
    
    def show_cancelled_stream_notification(self, user_message: str):
        notification_text = f"""⚠️ [yellow]AI response cancelled[/yellow]

[cyan]Original question:[/cyan] {user_message[:80]}{'...' if len(user_message) > 80 else ''}

[green]To resume:[/green]
• Press [bold]Alt+Z[/bold] or type [bold]resume[/bold]
• Type [bold]cancelstate[/bold] to see details

[dim]Partial response has been saved for resume[/dim]"""
        
        self.console.print(Panel(
            notification_text,
            title="🔄 Stream Cancelled",
            border_style="yellow",
            padding=(1, 2)
        ))
    
    def show_cancelled_stream_info(self, state_info: dict):
        user_message = state_info['user_message']
        word_count = state_info['partial_word_count']
        timestamp = state_info['timestamp']
        
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(timestamp)
            time_str = dt.strftime("%H:%M:%S")
        except:
            time_str = timestamp
        
        info_text = f"""[cyan]Cancelled Stream Details:[/cyan]

[bold]Original Question:[/bold] {user_message}
[bold]Partial Words:[/bold] {word_count}
[bold]Cancelled At:[/bold] {time_str}

[green]Available Actions:[/green]
• [bold]resume[/bold] - Continue from where it stopped
• [bold]Alt+Z[/bold] - Quick resume via keybinding
• [bold]clear[/bold] - Clear this cancelled state"""
        
        self.console.print(Panel(
            info_text,
            title="📋 Cancelled Stream State",
            border_style="cyan",
            padding=(1, 2)
        ))


class LiveMarkdownStreamRenderer:
    def __init__(self, console: Console, max_visible_lines: int = 20):
        self.console = console
        self.max_visible_lines = max_visible_lines
        self.rolling_buffer = []
        self.full_content = ""
        self.current_line = ""
        self.word_count = 0
        
    def reset(self):
        self.rolling_buffer = []
        self.full_content = ""
        self.current_line = ""
        self.word_count = 0
    
    def add_chunk(self, chunk: str):
        self.full_content += chunk
        self.current_line += chunk
        
        self.word_count = len(self.full_content.split())
        
        if '\n' in self.current_line:
            lines = self.current_line.split('\n')
            for completed_line in lines[:-1]:
                self.rolling_buffer.append(completed_line)
            self.current_line = lines[-1]
        
        if len(self.rolling_buffer) > self.max_visible_lines:
            self.rolling_buffer = self.rolling_buffer[-self.max_visible_lines:]
    
    def get_streaming_content(self):
        display_lines = self.rolling_buffer.copy()
        if self.current_line:
            display_lines.append(self.current_line + "▊")
        
        buffer_content = "\n".join(display_lines[-self.max_visible_lines:])
        
        if not buffer_content.strip():
            buffer_content = "🤔 Connecting to AI...▊"
        
        try:
            return Markdown(buffer_content)
        except Exception:
            return Text(buffer_content, overflow="fold")
    
    def get_final_content(self):
        try:
            return Markdown(self.full_content)
        except Exception:
            return Text(self.full_content, overflow="fold")
    
    def get_word_count(self):
        return self.word_count


class StreamingContentRenderer:
    
    def __init__(self):
        self.content = ""
    
    def update(self, new_content: str):
        self.content = new_content
    
    def __rich__(self):
        if not self.content:
            return Text("🤔 Waiting for response...")
        
        if "```" in self.content:
            try:
                return Markdown(self.content)
            except:
                return Text(self.content)
        elif any(indicator in self.content for indicator in ["def ", "import ", "class ", "function", "```"]):
            try:
                return Markdown(self.content)
            except:
                return Text(self.content)
        else:
            return Text(self.content, overflow="fold")


class StreamingUIManager:
    
    def __init__(self, console: Console):
        self.console = console
        self.markdown_renderer = LiveMarkdownStreamRenderer(console)
        self.cancelled_stream_state = None
    
    def create_streaming_layout(self, streaming_content=None):
        if streaming_content is None:
            streaming_content = self.markdown_renderer
            
        status_prog = Progress(
            SpinnerColumn("point"),
            TextColumn("{task.description}"),
            transient=True
        )
        status_id = status_prog.add_task("🤖 Connecting to AI...", total=None)
        
        counter_prog = Progress(
            TimeElapsedColumn(),
            TextColumn("Words: {task.completed} | Streaming..."),
        )
        counter_id = counter_prog.add_task("", total=None)
        
        layout_group = Group(
            status_prog,
            Panel(
                streaming_content,
                title="🤖 AI Assistant Response",
                border_style="green",
                padding=(1, 2)
            ),
            counter_prog
        )
        
        return layout_group, status_prog, status_id, counter_prog, counter_id
    
    def stream_ai_response_with_live_markdown(self, api_call_func, *args, **kwargs):

        self.markdown_renderer.reset()
        
        progress = Progress(
            SpinnerColumn("point"),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=None),
            TaskProgressColumn(),   
            MofNCompleteColumn(),      
            TextColumn("•"),
            TimeElapsedColumn(),
            transient=False,
        )
        
        with Live(console=self.console, refresh_per_second=12) as live:
            try:
                task_id = progress.add_task("🤖 Preparing AI connection...", total=None)
                
                initial_layout = Group(
                    progress,
                    Panel(
                        Align.center("🔄 Establishing connection to AI service..."),
                        title="🤖 AI Assistant",
                        border_style="blue",
                        padding=(1, 2)
                    )
                )
                
                live.update(initial_layout)
                
                first_chunk_received = False
                estimated_total_words = 100  # Initial estimate
                
                for chunk in api_call_func(*args, **kwargs):
                    if not first_chunk_received:
                        first_chunk_received = True
                        progress.update(
                            task_id, 
                            description="🚀 AI Streaming Response", 
                            total=estimated_total_words, 
                            completed=0
                        )
                    
                    self.markdown_renderer.add_chunk(chunk)
                    
                    streaming_content = self.markdown_renderer.get_streaming_content()
                    current_word_count = self.markdown_renderer.get_word_count()
                    
                    if current_word_count > estimated_total_words * 0.8:
                        estimated_total_words = max(
                            estimated_total_words * 1.5,
                            current_word_count + 50
                        )
                        progress.update(task_id, total=int(estimated_total_words))
                    
                    progress.update(
                        task_id,
                        completed=current_word_count,
                        description=f"🚀 Streaming • {current_word_count} words"
                    )
                    
                    layout = Group(
                        progress,
                        Panel(
                            streaming_content,
                            title="🤖 AI Assistant Response",
                            border_style="yellow",
                            padding=(0, 1)
                        )
                    )
                    
                    live.update(layout)
                
                final_content = self.markdown_renderer.get_final_content()
                final_word_count = self.markdown_renderer.get_word_count()
                
                progress.update(
                    task_id, 
                    total=final_word_count, 
                    completed=final_word_count, 
                    description=f"✅ Complete • {final_word_count} words",
                )
                
                final_layout = Group(
                    progress,
                    Panel(
                        final_content,
                        title="🤖 AI Assistant - Complete",
                        border_style="green",
                        padding=(0, 1)
                    )
                )
                
                live.update(final_layout)
                
                return self.markdown_renderer.full_content
                
            except KeyboardInterrupt:
                current_word_count = self.markdown_renderer.get_word_count()
                progress.update(
                    task_id, 
                    total=max(current_word_count, 1), 
                    completed=max(current_word_count, 1),
                    description="⚠️ Cancelled by user"
                )
                
                partial_content = self.markdown_renderer.get_final_content() if self.markdown_renderer.full_content else Align.center("⚠️ Response cancelled by user")
                
                cancelled_layout = Group(
                    progress,
                    Panel(
                        partial_content,
                        title="🤖 AI Assistant - Cancelled",
                        border_style="yellow",
                        padding=(1, 2)
                    )
                )
                
                live.update(cancelled_layout)
                                
                return "⚠️ Response cancelled"
                
            except Exception as e:
                progress.update(
                    task_id, 
                    total=1, 
                    completed=1,
                    description="❌ Connection error"
                )
                
                error_layout = Group(
                    progress,
                    Panel(
                        f"❌ Error: {str(e)}",
                        title="🤖 AI Assistant - Error",
                        border_style="red",
                        padding=(1, 2)
                    )
                )
                
                live.update(error_layout)
                return f"❌ Error: {str(e)}"
    
    def save_cancelled_state(self, user_message: str, partial_content: str, messages: list):
        self.cancelled_stream_state = {
            'user_message': user_message,
            'partial_content': partial_content,
            'messages': messages,
            'timestamp': datetime.now().isoformat(),
            'word_count': self.markdown_renderer.get_word_count()
        }
    
    def has_cancelled_stream(self) -> bool:
        return self.cancelled_stream_state is not None
    
    def clear_cancelled_state(self):
        self.cancelled_stream_state = None
    
    def get_cancelled_state_info(self) -> dict:
        if not self.has_cancelled_stream():
            return None
        
        return {
            'user_message': self.cancelled_stream_state['user_message'],
            'partial_word_count': self.cancelled_stream_state['word_count'],
            'timestamp': self.cancelled_stream_state['timestamp']
        }
    
    def stream_ai_response_with_resume(self, api_call_func, *args, **kwargs):
 
        if self.has_cancelled_stream():
            return self._resume_cancelled_stream(api_call_func, *args, **kwargs)
        else:
            return self.stream_ai_response_with_live_markdown(api_call_func, *args, **kwargs)
    
    def _resume_cancelled_stream(self, api_call_func, *args, **kwargs):

        if not self.has_cancelled_stream():
            return "❌ No cancelled stream to resume"
        
        saved_state = self.cancelled_stream_state
        user_message = saved_state['user_message']
        partial_content = saved_state['partial_content']
        original_messages = saved_state['messages']
        
        self.markdown_renderer.reset()
        self.markdown_renderer.full_content = partial_content
        self.markdown_renderer.current_line = ""
        
        self.markdown_renderer.word_count = len(partial_content.split())
        
        progress = Progress(
            SpinnerColumn("point"),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=None),
            TaskProgressColumn(),
            MofNCompleteColumn(),
            TextColumn("•"),
            TimeElapsedColumn(),
            transient=False,
        )
        
        with Live(console=self.console, refresh_per_second=12) as live:
            try:
                task_id = progress.add_task("🔄 Resuming AI response...", total=None)
                
                resume_layout = Group(
                    progress,
                    Panel(
                        Align.center(f"🔄 Resuming response to: '{user_message[:50]}{'...' if len(user_message) > 50 else ''}'"),
                        title="🤖 AI Assistant - Resume",
                        border_style="yellow",
                        padding=(1, 2)
                    )
                )
                live.update(resume_layout)
                
                first_chunk_received = False
                estimated_total_words = max(100, self.markdown_renderer.get_word_count() + 50)
                
                for chunk in api_call_func(*args, **kwargs):
                    if not first_chunk_received:
                        first_chunk_received = True
                        progress.update(
                            task_id, 
                            description="🚀 Resuming AI Response", 
                            total=estimated_total_words, 
                            completed=self.markdown_renderer.get_word_count()
                        )
                    
                    self.markdown_renderer.add_chunk(chunk)
                    
                    streaming_content = self.markdown_renderer.get_streaming_content()
                    current_word_count = self.markdown_renderer.get_word_count()
                    
                    if current_word_count > estimated_total_words * 0.8:
                        estimated_total_words = max(
                            estimated_total_words * 1.5,
                            current_word_count + 50
                        )
                        progress.update(task_id, total=int(estimated_total_words))
                    
                    progress.update(
                        task_id,
                        completed=current_word_count,
                        description=f"🚀 Resuming • {current_word_count} words"
                    )
                    
                    layout = Group(
                        progress,
                        Panel(
                            streaming_content,
                            title="🤖 AI Assistant - Resuming",
                            border_style="yellow",
                            padding=(0, 1)
                        )
                    )
                    
                    live.update(layout)
                
                final_content = self.markdown_renderer.get_final_content()
                final_word_count = self.markdown_renderer.get_word_count()
                
                progress.update(
                    task_id, 
                    total=final_word_count, 
                    completed=final_word_count, 
                    description=f"✅ Resume Complete • {final_word_count} words",
                )
                
                final_layout = Group(
                    progress,
                    Panel(
                        final_content,
                        title="🤖 AI Assistant - Resume Complete",
                        border_style="green",
                        padding=(0, 1)
                    )
                )
                
                live.update(final_layout)
                
                self.clear_cancelled_state()
                
                return self.markdown_renderer.full_content
                
            except KeyboardInterrupt:
                current_word_count = self.markdown_renderer.get_word_count()
                progress.update(
                    task_id, 
                    total=max(current_word_count, 1), 
                    completed=max(current_word_count, 1),
                    description="⚠️ Resume cancelled by user"
                )
                
                self.save_cancelled_state(
                    user_message, 
                    self.markdown_renderer.full_content, 
                    original_messages
                )
                
                partial_content = self.markdown_renderer.get_final_content() if self.markdown_renderer.full_content else Align.center("⚠️ Resume cancelled by user")
                
                cancelled_layout = Group(
                    progress,
                    Panel(
                        partial_content,
                        title="🤖 AI Assistant - Resume Cancelled",
                        border_style="yellow",
                        padding=(1, 2)
                    )
                )
                
                live.update(cancelled_layout)
                return "⚠️ Resume cancelled"
                
            except Exception as e:
                progress.update(
                    task_id, 
                    total=1, 
                    completed=1,
                    description="❌ Resume error"
                )
                
                error_layout = Group(
                    progress,
                    Panel(
                        f"❌ Resume Error: {str(e)}",
                        title="🤖 AI Assistant - Resume Error",
                        border_style="red",
                        padding=(1, 2)
                    )
                )
                
                live.update(error_layout)
                return f"❌ Resume Error: {str(e)}"


class ContextManager:
    
    def __init__(self):
        self.shell_context = []
        self.conversation_history = []
    
    def add_shell_context(self, command: str, output: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        context_entry = {
            "timestamp": timestamp,
            "command": command,
            "output": output,
            "cwd": os.getcwd(),
            "epoch_time": datetime.now().timestamp()
        }
        self.shell_context.append(context_entry)
        
        if len(self.shell_context) > Config.MAX_SHELL_CONTEXT:
            self.shell_context.pop(0)
    
    def build_context_for_ai(self) -> str:
        if not self.shell_context:
            return ""
        
        recent_contexts = sorted(self.shell_context, 
                               key=lambda x: x.get('epoch_time', 0), 
                               reverse=True)
        
        context_parts = ["Recent shell activity (prioritized by recency):"]
        
        priority_contexts = recent_contexts[:3]
        if priority_contexts:
            context_parts.append("\n🔥 MOST RECENT COMMANDS:")
            for i, entry in enumerate(priority_contexts):
                priority_marker = ">>> LATEST:" if i == 0 else f">>> #{i+1}:"
                context_parts.append(f"\n{priority_marker} [{entry['timestamp']}] In: {entry['cwd']}")
                context_parts.append(f"Command: {entry['command']}")
                
                if entry['output']:
                    output = entry['output']
                    max_length = 800 if i == 0 else 400  
                    if len(output) > max_length:
                        output = output[:max_length] + "... (truncated)"
                    context_parts.append(f"Output: {output}")
                context_parts.append("-" * 50)
        
        older_contexts = recent_contexts[3:Config.CONTEXT_FOR_AI]
        if older_contexts:
            context_parts.append("\n📋 ADDITIONAL CONTEXT (older commands):")
            for entry in older_contexts:
                context_parts.append(f"[{entry['timestamp']}] {entry['command']} -> {entry['output'][:100]}...")
        
        context_parts.append("\n💡 NOTE: When user asks about errors or issues, prioritize the LATEST/MOST RECENT commands above.")
        
        return "\n".join(context_parts)
    
    def get_latest_command_context(self) -> dict:
        if not self.shell_context:
            return None
        
        recent_contexts = sorted(self.shell_context, 
                               key=lambda x: x.get('epoch_time', 0), 
                               reverse=True)
        return recent_contexts[0]
    
    def add_conversation(self, user_message: str, ai_response: str):
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        self.conversation_history.append({
            "role": "assistant", 
            "content": ai_response
        })
        
        if len(self.conversation_history) > Config.MAX_CONVERSATION_HISTORY:
            self.conversation_history = self.conversation_history[-Config.MAX_CONVERSATION_HISTORY:]
    
    def clear_context(self):
        self.shell_context = []
    
    def clear_conversation(self):
        self.conversation_history = []
    
    def clear_all(self):
        self.clear_context()
        self.clear_conversation()
    
    def save_history(self, filepath: str = None):
        if filepath is None:
            filepath = Config.HISTORY_FILE
        
        try:
            Config.ensure_directories()
            with open(filepath, 'w') as f:
                json.dump(self.conversation_history, f, indent=2)
        except Exception as e:
            print(f"Failed to save history: {e}")
    
    def load_history(self, filepath: str = None):
        if filepath is None:
            filepath = Config.HISTORY_FILE
        
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    self.conversation_history = json.load(f)
        except Exception as e:
            print(f"Failed to load history: {e}")
            self.conversation_history = []


class EnhancedContextManager(ContextManager):
    
    def build_context_for_ai(self) -> str:
        context_parts = []
        
        env_info = get_all_env_info()
        if any(env_info.values()):  
            context_parts.append("🌍 CURRENT ENVIRONMENT:")
            
            if env_info.get('python'):
                py_env = env_info['python']
                context_parts.append(f"Python: {py_env['display']} (v{py_env['python_version']}) - {py_env['type']}")
            
            if env_info.get('git'):
                git_info = env_info['git']
                status = "clean" if not git_info.get('has_changes') else "modified"
                ahead_behind = ""
                if git_info.get('ahead', 0) > 0:
                    ahead_behind += f" ↑{git_info['ahead']}"
                if git_info.get('behind', 0) > 0:
                    ahead_behind += f" ↓{git_info['behind']}"
                context_parts.append(f"Git: branch '{git_info['branch']}' ({status}){ahead_behind}")
            
            if env_info.get('node'):
                node_info = env_info['node']
                context_parts.append(f"Node.js: {node_info['name']} v{node_info['version']}")
            
            if env_info.get('docker'):
                docker_info = env_info['docker']
                context_parts.append(f"Docker: {docker_info['display']}")
            
            context_parts.append("-" * 60)
        
        shell_context = super().build_context_for_ai()
        if shell_context:
            context_parts.append(shell_context)
        
        return "\n".join(context_parts)


def create_streaming_api_generator(api_response_iterator):

    for chunk in api_response_iterator:
        if chunk:
            yield chunk


def example_integration_with_existing_streaming():
    console = Console()
    ui_manager = StreamingUIManager(console)
    
    def mock_api_streaming():
        """Mock API function that yields content chunks"""
        sample_content = [
            "# Hello World\n\n",
            "This is a **streaming** response with:\n\n",
            "- Enhanced BarColumn progress\n",
            "- Live markdown rendering\n", 
            "- Rolling buffer effect\n",
            "- Smooth progress tracking\n\n",
            "```python\n",
            "def example():\n",
            "    return 'enhanced streaming!'\n",
            "```\n\n",
            "Progress bar shows real-time word count!\n",
            "And updates dynamically as content grows.\n\n",
            "The bar column provides visual feedback\n",
            "while maintaining all existing functionality.\n"
        ]
        
        for chunk in sample_content:
            time.sleep(0.3)
            yield chunk
    
    response = ui_manager.stream_ai_response_with_live_markdown(mock_api_streaming)
    return response

def create_custom_progress_style():
    return Progress(
        TextColumn("["),
        SpinnerColumn("point"),
        TextColumn("]"), 
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(
            bar_width=None,
            style="cyan",
            complete_style="green",
            finished_style="green"
        ),
        TaskProgressColumn(text_format="{task.percentage:>3.0f}%"),
        MofNCompleteColumn(),
        TextColumn("•"),
        TimeElapsedColumn(),
        transient=False
    )


def handle_environment_commands(command: str, ui_manager: UIManager) -> bool:

    command = command.strip()
    
    if command == "!env":
        ui_manager.show_environment_status()
        return True
    
    elif command == "!status":
        status_info = get_status_info()
        ui_manager.console.print(Panel(
            status_info,
            title="🔍 System & Environment Status",
            border_style="cyan"
        ))
        return True
    
    elif command == "!git":
        from environment import get_git_info
        git_info = get_git_info()
        if git_info:
            git_details = []
            git_details.append(f"Branch: {git_info['branch']}")
            git_details.append(f"Status: {'Clean' if not git_info.get('has_changes') else 'Modified'}")
            if git_info.get('ahead', 0) > 0:
                git_details.append(f"Ahead: {git_info['ahead']} commits")
            if git_info.get('behind', 0) > 0:
                git_details.append(f"Behind: {git_info['behind']} commits")
            
            ui_manager.console.print(Panel(
                "\n".join(git_details),
                title="📊 Git Repository Status",
                border_style="green"
            ))
        else:
            ui_manager.console.print(Panel(
                "[yellow]Not a git repository[/yellow]",
                title="📊 Git Status",
                border_style="yellow"
            ))
        return True
    
    elif command == "!python":
        from environment import get_python_env
        py_env = get_python_env()
        if py_env:
            py_details = []
            py_details.append(f"Environment: {py_env['display']}")
            py_details.append(f"Type: {py_env['type']}")
            py_details.append(f"Python Version: {py_env['python_version']}")
            if 'path' in py_env:
                py_details.append(f"Path: {py_env['path']}")
            
            ui_manager.console.print(Panel(
                "\n".join(py_details),
                title="🐍 Python Environment",
                border_style="blue"
            ))
        else:
            import sys
            ui_manager.console.print(Panel(
                f"System Python {'.'.join(map(str, sys.version_info[:3]))}\nNo virtual environment active",
                title="🐍 Python Environment",
                border_style="yellow"
            ))
        return True
    
    return False

def create_enhanced_ui_manager(console: Console, use_environment_context: bool = True) -> UIManager:

    return UIManager(console)


def create_enhanced_context_manager() -> EnhancedContextManager:

    return EnhancedContextManager()
