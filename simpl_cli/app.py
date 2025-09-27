#!/usr/bin/env python3
import os
import sys
import json
import subprocess
import requests
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.clipboard.pyperclip import PyperclipClipboard
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns

from .config import Config
from .customization import (
    UIManager, 
    LiveMarkdownStreamRenderer,
    StreamingUIManager, 
    ContextManager
)
from .completion import create_completion_manager
from .environment import env_detector


class HybridShell:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.mode = "shell"  # "shell" or "ai"
        self.session = PromptSession()
        self.console = Console()
        
        self.ui = UIManager(self.console)
        self.streaming_ui = StreamingUIManager(self.console)
        self.context_manager = ContextManager()
        
        self.completion_manager = create_completion_manager()
        
        self.setup_keybindings()
        
        self.context_manager.load_history()
        
    def setup_keybindings(self):
        self.bindings = KeyBindings()
        
        @self.bindings.add('c-a') 
        def switch_to_ai(event):
            self.mode = "ai"
            self.ui.show_mode_switch("AI Mode")
            
        @self.bindings.add('c-s') 
        def switch_to_shell(event):
            self.mode = "shell"
            self.ui.show_mode_switch("Shell Mode")
            
        @self.bindings.add('escape', 'h') 
        def show_help(event):
            self.ui.show_help()
            
        @self.bindings.add('escape', 'c') 
        def clear_context(event):
            self.context_manager.clear_all()
            self.ui.show_context_cleared()
            
        @self.bindings.add('escape', 'r') 
        def refresh_completion(event):
            self.completion_manager.clear_cache()
            
        @self.bindings.add('escape', 'z') 
        def resume_cancelled_stream(event):
            self.resume_cancelled_stream()

    def true_clear_terminal(self):
        clear_sequence = '\033[2J\033[H'
        sys.stdout.write(clear_sequence)
        sys.stdout.flush()
        
        try:
            if os.name == 'posix':
                os.system('clear')
            elif os.name == 'nt':
                os.system('cls')
        except:
            self.console.clear()

    def is_interactive_command(self, command: str) -> bool:
        base_cmd = command.strip().split()[0]
        
        if base_cmd in Config.INTERACTIVE_COMMANDS:
            return True
            
        if '|' in command:
            parts = command.split('|')
            for part in parts:
                if part.strip().split()[0] in Config.INTERACTIVE_COMMANDS:
                    return True
        
        return False

    def handle_environment_commands(self, command: str) -> bool:
        if not command.startswith('!'):
            return False
            
        env_cmd = command[1:]
        
        try:
            if env_cmd == "env":
                self._show_environment_status()
                self.context_manager.add_shell_context(command, "Environment status displayed")
                return True
            elif env_cmd == "status":
                self._show_detailed_system_info()
                self.context_manager.add_shell_context(command, "Detailed system information displayed")
                return True
            elif env_cmd == "git":
                self._show_git_info()
                self.context_manager.add_shell_context(command, "Git repository information displayed")
                return True
            elif env_cmd == "python":
                self._show_python_info()
                self.context_manager.add_shell_context(command, "Python environment information displayed")
                return True
            else:
                error_msg = f"Unknown environment command: {env_cmd}"
                self.ui.display_error(command, error_msg)
                self.context_manager.add_shell_context(command, f"Error: {error_msg}")
                return True
        except Exception as e:
            error_msg = f"Environment command error: {e}"
            self.ui.display_error(command, error_msg)
            self.context_manager.add_shell_context(command, f"Error: {error_msg}")
            return True
        
        return False

    def _show_environment_status(self):
        env_info = env_detector.get_all_environments()
        
        table = Table(title="Environment Status", show_header=True, header_style="bold magenta")
        table.add_column("Type", style="cyan", width=12)
        table.add_column("Status", style="green", width=20)
        table.add_column("Details", style="yellow")
        
        if env_info['python']:
            py_env = env_info['python']
            table.add_row(
                "Python", 
                py_env['name'], 
                f"v{py_env['python_version']} ({py_env['type']})"
            )
        else:
            table.add_row("Python", "System", f"v{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
        
        if env_info['git']:
            git_info = env_info['git']
            status_indicator = "🔴" if git_info.get('has_changes') else "🟢"
            table.add_row(
                "Git", 
                f"{status_indicator} {git_info['branch']}", 
                f"Ahead: {git_info.get('ahead', 0)}, Behind: {git_info.get('behind', 0)}"
            )
        else:
            table.add_row("Git", "Not a repository", "-")
        
        if env_info['node']:
            node_info = env_info['node']
            modules_status = "✓" if node_info['has_modules'] else "✗"
            table.add_row(
                "Node.js", 
                node_info['name'], 
                f"v{node_info['version']} (modules: {modules_status})"
            )
        else:
            table.add_row("Node.js", "Not detected", "-")
        
        if env_info['docker']:
            docker_info = env_info['docker']
            docker_details = []
            if docker_info.get('has_dockerfile'):
                docker_details.append("Dockerfile")
            if docker_info.get('has_compose'):
                docker_details.append("Compose")
            if docker_info.get('inside_container'):
                docker_details.append("In Container")
            
            table.add_row("Docker", "Available", ", ".join(docker_details) if docker_details else "Basic")
        else:
            table.add_row("Docker", "Not detected", "-")
        
        self.console.print(table)

    def _show_detailed_system_info(self):
        system_info = env_detector.get_system_info()
        env_info = env_detector.get_all_environments()
        
        system_text = f"""[bold cyan]System Resources[/bold cyan]
CPU Usage: {system_info['cpu_percent']:.1f}%
Memory Usage: {system_info['memory_percent']:.1f}%
Available Memory: {system_info['memory_available']}MB
Load Average: {system_info['load_average']:.2f}
Uptime: {system_info['uptime']}"""
        
        env_summary = "[bold green]Active Environments[/bold green]\n"
        active_envs = []
        
        if env_info['python']:
            active_envs.append(f"🐍 {env_info['python']['display']}")
        if env_info['git']:
            git_status = "🔴" if env_info['git'].get('has_changes') else "🟢"
            active_envs.append(f"{git_status} {env_info['git']['display']}")
        if env_info['node']:
            active_envs.append(f"📦 {env_info['node']['display']}")
        if env_info['docker']:
            active_envs.append(f"🐳 {env_info['docker']['display']}")
        
        if active_envs:
            env_summary += "\n".join(active_envs)
        else:
            env_summary += "No special environments detected"
        
        cwd = os.getcwd()
        dir_info = f"[bold yellow]Current Directory[/bold yellow]\n{cwd}"
        
        panels = [
            Panel(system_text, title="System", border_style="blue"),
            Panel(env_summary, title="Environments", border_style="green"),
            Panel(dir_info, title="Location", border_style="yellow")
        ]
        
        self.console.print(Columns(panels))

    def _show_git_info(self):
        git_info = env_detector.get_git_status()
        
        if not git_info:
            self.console.print("[red]Not in a Git repository[/red]")
            return
        
        table = Table(title="Git Repository Information", show_header=True)
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Branch", git_info['branch'])
        table.add_row("Status", "🔴 Modified" if git_info.get('has_changes') else "🟢 Clean")
        table.add_row("Commits Ahead", str(git_info.get('ahead', 0)))
        table.add_row("Commits Behind", str(git_info.get('behind', 0)))
        
        self.console.print(table)
        
        try:
            result = subprocess.run(['git', 'log', '--oneline', '-5'], 
                                  capture_output=True, text=True, timeout=3)
            if result.returncode == 0 and result.stdout:
                commits = result.stdout.strip()
                self.console.print(Panel(commits, title="Recent Commits", border_style="blue"))
        except:
            pass

    def _show_python_info(self):
        py_env = env_detector.get_python_environment()
        
        table = Table(title="Python Environment", show_header=True)
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Python Version", f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
        table.add_row("Python Executable", sys.executable)
        
        if py_env:
            table.add_row("Virtual Environment", py_env['name'])
            table.add_row("Environment Type", py_env['type'])
            if 'path' in py_env:
                table.add_row("Environment Path", py_env['path'])
        else:
            table.add_row("Virtual Environment", "None (System Python)")
        
        python_paths = sys.path[:3]
        if len(sys.path) > 3:
            python_paths.append("...")
        table.add_row("Python Path", "\n".join(python_paths))
        
        self.console.print(table)
        
        try:
            result = subprocess.run([sys.executable, '-m', 'pip', 'list'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[2:]
                if lines:
                    packages = '\n'.join(lines[:10])
                    if len(lines) > 10:
                        packages += f"\n... and {len(lines) - 10} more packages"
                    self.console.print(Panel(packages, title="Installed Packages (Top 10)", border_style="blue"))
        except:
            pass

    def _execute_source_like_command(self, original_command: str, bash_command: str):
        """Execute a source-like command and update environment"""
        try:
            old_env = dict(os.environ)
            
            with self.ui.create_status(f"Executing: {original_command}"):
                result = subprocess.run(
                    ['bash', '-c', bash_command],
                    capture_output=True,
                    text=True,
                    cwd=os.getcwd()
                )
            
            if result.returncode == 0:
                new_vars = {}
                changed_vars = {}
                
                for line in result.stdout.split('\n'):
                    if '=' in line and not line.startswith('_='):
                        try:
                            key, value = line.split('=', 1)
                            if key in ['PS1', 'PS2', 'BASH_FUNC_*', '_'] or key.startswith('BASH_FUNC_'):
                                continue
                                
                            if key not in old_env:
                                new_vars[key] = value
                            elif old_env[key] != value:
                                changed_vars[key] = {'old': old_env[key], 'new': value}
                                
                            os.environ[key] = value
                        except ValueError:
                            continue
                
                success_msg = f"✅ {original_command} completed successfully"
                if new_vars or changed_vars:
                    success_msg += f" ({len(new_vars)} new, {len(changed_vars)} changed variables)"
                
                self.console.print(f"[green]{success_msg}[/green]")
                self.context_manager.add_shell_context(original_command, success_msg)
                self._show_env_changes(new_vars, changed_vars)
                
            else:
                error_msg = f"{original_command}: {result.stderr.strip() or 'command failed'}"
                self.ui.display_error(original_command, error_msg)
                self.context_manager.add_shell_context(original_command, error_msg)
                
        except Exception as e:
            error_msg = f"{original_command}: {e}"
            self.ui.display_error(original_command, error_msg)
            self.context_manager.add_shell_context(original_command, error_msg)

    def _show_env_changes(self, new_vars: dict, changed_vars: dict):
        important_vars = ['PATH', 'VIRTUAL_ENV', 'CONDA_DEFAULT_ENV', 'NODE_ENV', 'PYTHONPATH', 'LD_LIBRARY_PATH', 'JAVA_HOME']
        
        if new_vars:
            self.console.print("[dim]New environment variables:[/dim]")
            count = 0
            for var, value in new_vars.items():
                if var in important_vars or count < 5: 
                    display_value = value
                    if len(display_value) > 60:
                        display_value = display_value[:57] + "..."
                    self.console.print(f"[dim green]  +{var}={display_value}[/dim green]")
                    count += 1
            
            if len(new_vars) > count:
                self.console.print(f"[dim]  ... and {len(new_vars) - count} more new variables[/dim]")
        
        if changed_vars:
            self.console.print("[dim]Changed environment variables:[/dim]")
            count = 0
            for var, values in changed_vars.items():
                if var in important_vars or count < 3:
                    old_val = values['old']
                    new_val = values['new']
                    
                    if len(old_val) > 30:
                        old_val = old_val[:27] + "..."
                    if len(new_val) > 30:
                        new_val = new_val[:27] + "..."
                        
                    self.console.print(f"[dim yellow]  ~{var}: {old_val} → {new_val}[/dim yellow]")
                    count += 1
            
            if len(changed_vars) > count:
                self.console.print(f"[dim]  ... and {len(changed_vars) - count} more changed variables[/dim]")

    def execute_shell_command(self, command: str):
        if not command.strip():
            return
            
        try:
            if self.handle_environment_commands(command):
                return
                
            if command.strip() == "exit":
                return "exit"
            elif command.strip() == "clear":
                self.true_clear_terminal()
                return
            elif command.strip().startswith("cd "):
                result = self._handle_cd_command(command)
                self.completion_manager.update_cache()
                return result
            
            elif command.strip().startswith("source "):
                self._handle_source_command(command)
                return
            
            elif command.strip() == "deactivate":
                self._handle_deactivate_command(command)
                return
            
            elif (command.strip().endswith("/activate") or 
                  command.strip().endswith("\\activate") or
                  command.strip().startswith("activate ")):
                self._handle_activate_command(command)
                return

            if self.is_interactive_command(command):
                self._handle_interactive_command(command)
                return

            self._handle_regular_command(command)
                
        except KeyboardInterrupt:
            self.ui.display_interrupt()
        except Exception as e:
            self.ui.display_error(command, f"Error: {e}")
            self.context_manager.add_shell_context(command, f"Error: {e}")

    def _handle_source_command(self, command: str):
        source_file = command.strip()[7:].strip()
        
        if not source_file:
            error_msg = "source: missing file operand"
            self.ui.display_error(command, error_msg)
            self.context_manager.add_shell_context(command, error_msg)
            return
        
        source_file = os.path.expanduser(source_file)
        
        if not os.path.exists(source_file):
            error_msg = f"source: {source_file}: No such file or directory"
            self.ui.display_error(command, error_msg)
            self.context_manager.add_shell_context(command, error_msg)
            return
        
        bash_command = f'source "{source_file}" && env'
        self._execute_source_like_command(command, bash_command)

    def _handle_deactivate_command(self, command: str):
        try:
            virtual_env = os.environ.get('VIRTUAL_ENV')
            conda_env = os.environ.get('CONDA_DEFAULT_ENV')
            
            if not virtual_env and not conda_env:
                error_msg = "deactivate: No virtual environment currently activated"
                self.ui.display_error(command, error_msg)
                self.context_manager.add_shell_context(command, error_msg)
                return
            
            env_name = ""
            env_type = ""
            
            if virtual_env:
                env_name = os.path.basename(virtual_env)
                env_type = "virtualenv/venv"
            elif conda_env and conda_env != "base":
                env_name = conda_env
                env_type = "conda"
            
            with self.ui.create_status("Deactivating virtual environment..."):
                if virtual_env:
                    current_path = os.environ.get('PATH', '')
                    venv_bin = os.path.join(virtual_env, 'bin')
                    path_parts = current_path.split(os.pathsep)
                    new_path_parts = []
                    
                    for part in path_parts:
                        if not part.startswith(venv_bin):
                            new_path_parts.append(part)
                    
                    os.environ['PATH'] = os.pathsep.join(new_path_parts)
                    
                    env_vars_to_remove = ['VIRTUAL_ENV', 'VIRTUAL_ENV_PROMPT']
                    removed_vars = []
                    
                    for var in env_vars_to_remove:
                        if var in os.environ:
                            del os.environ[var]
                            removed_vars.append(var)
                    
                    original_ps1 = os.environ.get('_OLD_VIRTUAL_PS1')
                    if original_ps1:
                        os.environ['PS1'] = original_ps1
                        del os.environ['_OLD_VIRTUAL_PS1']
                        removed_vars.append('_OLD_VIRTUAL_PS1')
                
                elif conda_env:
                    conda_vars_to_remove = ['CONDA_DEFAULT_ENV', 'CONDA_PREFIX', 'CONDA_PYTHON_EXE']
                    removed_vars = []
                    
                    for var in conda_vars_to_remove:
                        if var in os.environ:
                            del os.environ[var]
                            removed_vars.append(var)
                    
                    conda_base = os.environ.get('CONDA_EXE')
                    if conda_base:
                        conda_base_bin = os.path.dirname(conda_base)
                        current_path = os.environ.get('PATH', '')
                        
                        if conda_base_bin not in current_path:
                            os.environ['PATH'] = f"{conda_base_bin}{os.pathsep}{current_path}"
            
            success_msg = f"✅ Deactivated {env_type} environment: {env_name}"
            self.console.print(f"[green]{success_msg}[/green]")
            self.context_manager.add_shell_context(command, success_msg)
            
            if 'removed_vars' in locals() and removed_vars:
                self.console.print(f"[dim]Removed environment variables: {', '.join(removed_vars)}[/dim]")
            
            current_path = os.environ.get('PATH', '')
            path_parts = current_path.split(os.pathsep)[:3]
            self.console.print(f"[dim]Updated PATH: {os.pathsep.join(path_parts)}...[/dim]")
            
        except Exception as e:
            error_msg = f"deactivate: Error deactivating environment: {e}"
            self.ui.display_error(command, error_msg)
            self.context_manager.add_shell_context(command, error_msg)

    def _handle_activate_command(self, command: str):
        try:
            activate_path = ""
            
            if command.strip().endswith("/activate") or command.strip().endswith("\\activate"):
                activate_path = command.strip()
            elif command.strip().startswith("activate "):
                env_name = command.strip()[9:].strip()
                conda_exe = os.environ.get('CONDA_EXE')
                if conda_exe:
                    bash_command = f'source "{os.path.dirname(conda_exe)}/activate" && conda activate {env_name} && env'
                    self._execute_source_like_command(command, bash_command)
                    return
                else:
                    error_msg = f"activate: conda not found, cannot activate environment '{env_name}'"
                    self.ui.display_error(command, error_msg)
                    self.context_manager.add_shell_context(command, error_msg)
                    return
            
            if activate_path:
                activate_path = os.path.expanduser(activate_path)
                
                if not os.path.exists(activate_path):
                    error_msg = f"activate: {activate_path}: No such file or directory"
                    self.ui.display_error(command, error_msg)
                    self.context_manager.add_shell_context(command, error_msg)
                    return
                
                bash_command = f'source "{activate_path}" && env'
                self._execute_source_like_command(command, bash_command)
                
        except Exception as e:
            error_msg = f"activate: {e}"
            self.ui.display_error(command, error_msg)
            self.context_manager.add_shell_context(command, error_msg)

    def _handle_cd_command(self, command: str):
        path = command.strip()[3:].strip()
        if not path:
            path = os.path.expanduser("~")
        else:
            path = os.path.expanduser(path)
        
        try:
            os.chdir(path)
            new_dir = os.getcwd()
            self.ui.display_directory_change(command, new_dir)
            self.context_manager.add_shell_context(command, f"Changed directory to: {new_dir}")
        except OSError as e:
            error_msg = f"cd: {e}"
            self.ui.display_error(command, error_msg)
            self.context_manager.add_shell_context(command, error_msg)

    def _handle_interactive_command(self, command: str):
        try:
            self.ui.display_interactive_start(command)
            
            result = subprocess.run(command, shell=True, cwd=os.getcwd())
            
            self.ui.display_interactive_end(command, result.returncode)
            
            context_msg = f"Interactive command completed with exit code: {result.returncode}"
            self.context_manager.add_shell_context(command, context_msg)
            
        except KeyboardInterrupt:
            self.ui.display_interrupt("Interactive mode interrupted")
            self.context_manager.add_shell_context(command, "Interactive command interrupted by user")
        except Exception as e:
            error_msg = f"Error running interactive command: {e}"
            self.ui.display_error(command, error_msg)
            self.context_manager.add_shell_context(command, error_msg)

    def _handle_regular_command(self, command: str):
        bash_builtins = ['source', 'export', 'unset', 'alias', 'unalias', 'declare', 'typeset', 'readonly']
        command_parts = command.strip().split()
        base_command = command_parts[0] if command_parts else ""
        
        needs_bash = (
            'source ' in command or 
            command.strip().startswith('source') or
            base_command in bash_builtins or
            '&&' in command or 
            '||' in command or
            ';' in command or
            'export ' in command or
            'unset ' in command
        )
        
        if needs_bash:
            with self.ui.create_status(f"Executing: {command}"):
                result = subprocess.run(
                    ['bash', '-c', command],
                    capture_output=True, 
                    text=True,
                    cwd=os.getcwd(),
                    env=os.environ.copy()
                )
        else:
            with self.ui.create_status(f"Executing: {command}"):
                result = subprocess.run(
                    command, 
                    shell=True, 
                    capture_output=True, 
                    text=True,
                    cwd=os.getcwd()
                )
        
        self.ui.display_shell_output(command, result)
        
        output = result.stdout + result.stderr
        self.context_manager.add_shell_context(command, output)
        
        self._update_completion_if_needed(command)

    def _update_completion_if_needed(self, command: str):
        modify_commands = ['touch', 'mkdir', 'rm', 'rmdir', 'mv', 'cp', 'ln']
        base_cmd = command.strip().split()[0]
        
        if base_cmd in modify_commands:
            self.completion_manager.update_cache()

    def create_api_streaming_generator(self, messages):
        url = Config.API_BASE_URL
        payload = {
            "model": Config.get_model_name(),
            "messages": messages,
            "stream": True,
            **Config.AI_CONFIG
        }
        headers = {
            "Accept": "text/event-stream",
            "Content-Type": "application/json", 
            "Authorization": f"Bearer {self.api_key}"
        }
        
        try:
            response = requests.post(
                url, 
                headers=headers, 
                data=json.dumps(payload), 
                stream=True,
                timeout=Config.API_TIMEOUT
            )
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    
                    if not line_str.startswith('data: '):
                        continue
                        
                    json_str = line_str[6:]
                    
                    if json_str.strip() == '[DONE]':
                        break
                        
                    try:
                        chunk_data = json.loads(json_str)
                        
                        if 'choices' in chunk_data and len(chunk_data['choices']) > 0:
                            delta = chunk_data['choices'][0].get('delta', {})
                            content = delta.get('content', '')
                            
                            if content:
                                yield content
                                
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            yield f"Error: {str(e)}"

    def stream_ai_response(self, user_message: str):
        messages = []
        
        context = self.context_manager.build_context_for_ai()
        if context:
            messages.append({
                "role": "system",
                "content": f"You are a helpful AI assistant integrated with a shell environment. {context}\n\nUse this context to provide relevant answers about files, directories, or commands the user has executed."
            })
        
        messages.extend(self.context_manager.conversation_history)
        
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        def api_streaming_func():
            return self.create_api_streaming_generator(messages)
        
        try:
            response = self.streaming_ui.stream_ai_response_with_live_markdown(api_streaming_func)
            
            if response == "⚠️ Response cancelled":
                partial_content = self.streaming_ui.markdown_renderer.full_content
                self.streaming_ui.save_cancelled_state(user_message, partial_content, messages)
                self.ui.show_cancelled_stream_notification(user_message)
            elif response and not response.startswith("❌") and not response.startswith("⚠️"):
                self.context_manager.add_conversation(user_message, response)
                
            return response
            
        except Exception as e:
            error_msg = f"❌ Streaming error: {str(e)}"
            self.console.print(f"[red]{error_msg}[/red]")
            return error_msg

    def resume_cancelled_stream(self):
        if not self.streaming_ui.has_cancelled_stream():
            self.console.print(Panel(
                "[yellow]No cancelled stream to resume[/yellow]",
                title="Resume Stream",
                border_style="yellow"
            ))
            return
        
        state_info = self.streaming_ui.get_cancelled_state_info()
        user_message = state_info['user_message']
        
        self.console.print("")
        self.console.print(Panel(
            f"[cyan]Resuming response to: '{user_message[:60]}{'...' if len(user_message) > 60 else ''}'[/cyan]",
            title="🔄 Resume Stream",
            border_style="cyan"
        ))
        
        def api_streaming_func():
            original_messages = self.streaming_ui.cancelled_stream_state['messages']
            return self.create_api_streaming_generator(original_messages)
        
        try:
            response = self.streaming_ui.stream_ai_response_with_resume(api_streaming_func)
            
            if response and not response.startswith("❌") and not response.startswith("⚠️"):
                self.context_manager.add_conversation(user_message, response)
                
            return response
            
        except Exception as e:
            error_msg = f"❌ Resume error: {str(e)}"
            self.console.print(f"[red]{error_msg}[/red]")
            return error_msg

    def handle_ai_special_commands(self, user_input: str) -> bool:
        """Handle special AI mode commands. Returns True if handled."""
        if user_input.lower() == "clear0":
            self.context_manager.clear_conversation()
            self.ui.show_conversation_cleared()
            return True
        elif user_input.lower() == "clear":
            self.context_manager.clear_all()
            self.ui.show_context_cleared()
            return True
        elif user_input.lower() == "context":
            self.ui.show_context_table(self.context_manager.shell_context)
            return True
        elif user_input.lower() == "resume":
            self.resume_cancelled_stream()
            return True
        elif user_input.lower() == "cancelstate":
            if self.streaming_ui.has_cancelled_stream():
                state_info = self.streaming_ui.get_cancelled_state_info()
                self.ui.show_cancelled_stream_info(state_info)
            else:
                self.console.print(Panel(
                    "[yellow]No cancelled stream available[/yellow]",
                    title="Cancel State",
                    border_style="yellow"
                ))
            return True
        return False

    def handle_shell_special_commands(self, user_input: str) -> bool:
        return False

    def run(self):
        self.ui.show_welcome()

        session_history = AutoSuggestFromHistory()
        
        try:
            while True:
                try:
                    current_completer = None
                    if self.mode == "shell":
                        current_completer = self.completion_manager.get_completer()
                    
                    user_input = self.session.prompt(
                        self.ui.get_prompt_text(self.mode),
                        key_bindings=self.bindings,
                        style=self.ui.get_style(),
                        auto_suggest=session_history,
                        clipboard=PyperclipClipboard(),
                        completer=current_completer,
                        complete_while_typing=True,
                    ).strip()
                    
                    if not user_input:
                        continue
                        
                    if self.mode == "ai":
                        if self.handle_ai_special_commands(user_input):
                            continue
                            
                        self.stream_ai_response(user_input)
                        self.console.print()
                        
                    else:
                        if self.handle_shell_special_commands(user_input):
                            continue
                            
                        result = self.execute_shell_command(user_input)
                        if result == "exit":
                            break
                            
                except KeyboardInterrupt:
                    self.ui.display_goodbye()
                    break
                    
        except KeyboardInterrupt:
            self.ui.display_goodbye()
        finally:
            self.context_manager.save_history()


def check_dependencies():
    try:
        import rich
        import prompt_toolkit
        import requests
        import psutil
    except ImportError as e:
        print(f"❌ Required dependency not found: {e}")
        print("Please install required packages:")
        print("pip install rich prompt-toolkit requests psutil")
        
        try:
            import tomli
        except ImportError:
            print("Optional: pip install tomli (for Poetry project detection)")
        
        sys.exit(1)


def get_api_key():
    api_key = Config.get_api_key()
    
    if not api_key:
        console = Console()
        console.print("🔑 [yellow]API Key not found in environment variables.[/yellow]")
        console.print("Set FIREWORKS_API_KEY environment variable or enter it now:")
        api_key = console.input("Fireworks API Key: ").strip()
        
        if not api_key:
            console.print("❌ [red]API Key required to run the hybrid shell[/red]")
            sys.exit(1)
    
    return api_key


def main():
    check_dependencies()
    
    Config.ensure_directories()

    api_key = get_api_key()

    shell = HybridShell(api_key)
    shell.run()

if __name__ == "__main__":
    main()
