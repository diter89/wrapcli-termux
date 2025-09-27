#!/usr/bin/env python3
import os
import glob
import stat
import pwd
import grp
from datetime import datetime
from typing import List, Dict, Set, Optional, Tuple
from prompt_toolkit.completion import FuzzyWordCompleter, Completer, Completion
from prompt_toolkit.document import Document


class FileMetadata:
    
    def __init__(self):
        self._metadata_cache = {}
    
    def get_file_info(self, file_path: str) -> str:

        if file_path in self._metadata_cache:
            return self._metadata_cache[file_path]
        
        try:
            stat_info = os.stat(file_path)
            
            if os.path.isdir(file_path):
                file_type = "📁 Directory"
            elif os.path.islink(file_path):
                file_type = "🔗 Symlink"
            elif os.access(file_path, os.X_OK):
                file_type = "🔧 Executable"
            else:
                _, ext = os.path.splitext(file_path)
                file_type = self._get_file_type_by_extension(ext.lower())
            
            size = stat_info.st_size
            size_str = self._format_size(size)
            
            perms = stat.filemode(stat_info.st_mode)
            
            try:
                owner = pwd.getpwuid(stat_info.st_uid).pw_name
                group = grp.getgrgid(stat_info.st_gid).gr_name
            except (KeyError, OSError):
                owner = str(stat_info.st_uid)
                group = str(stat_info.st_gid)
            
            mtime = datetime.fromtimestamp(stat_info.st_mtime)
            mtime_str = mtime.strftime("%Y-%m-%d %H:%M")
            
            meta_info = f"{file_type} | {size_str} | {perms} | {owner}:{group} | {mtime_str}"
            
            self._metadata_cache[file_path] = meta_info
            return meta_info
            
        except (OSError, PermissionError, FileNotFoundError):
            return "❌ Access denied or file not found"
    
    def _get_file_type_by_extension(self, ext: str) -> str:
        """Map file extensions to descriptive types with emojis"""
        type_map = {
            '.py': '🐍 Python',
            '.js': '🟨 JavaScript',
            '.ts': '🔷 TypeScript',
            '.html': '🌐 HTML',
            '.css': '🎨 CSS',
            '.json': '📋 JSON',
            '.xml': '📄 XML',
            '.yaml': '⚙️ YAML',
            '.yml': '⚙️ YAML',
            '.md': '📝 Markdown',
            '.txt': '📄 Text',
            '.log': '📜 Log',
            '.conf': '⚙️ Config',
            '.cfg': '⚙️ Config',
            '.ini': '⚙️ Config',
            '.sh': '📜 Shell Script',
            '.bash': '📜 Bash Script',
            '.zsh': '📜 Zsh Script',
            '.fish': '🐟 Fish Script',
            '.jpg': '🖼️ JPEG Image',
            '.jpeg': '🖼️ JPEG Image',
            '.png': '🖼️ PNG Image',
            '.gif': '🖼️ GIF Image',
            '.svg': '🖼️ SVG Image',
            '.pdf': '📕 PDF',
            '.doc': '📄 Word Doc',
            '.docx': '📄 Word Doc',
            '.xls': '📊 Excel',
            '.xlsx': '📊 Excel',
            '.zip': '🗜️ ZIP Archive',
            '.tar': '🗜️ TAR Archive',
            '.gz': '🗜️ GZip Archive',
            '.rar': '🗜️ RAR Archive',
            '.7z': '🗜️ 7Z Archive',
            '.mp3': '🎵 MP3 Audio',
            '.mp4': '🎬 MP4 Video',
            '.avi': '🎬 AVI Video',
            '.mov': '🎬 MOV Video',
            '.wav': '🎵 WAV Audio',
            '.flac': '🎵 FLAC Audio',
        }
        
        return type_map.get(ext, '📄 File')
    
    def _format_size(self, size_bytes: int) -> str:
        if size_bytes == 0:
            return "0 B"
        
        size_names = ['B', 'KB', 'MB', 'GB', 'TB']
        i = 0
        size = float(size_bytes)
        
        while size >= 1024.0 and i < len(size_names) - 1:
            size /= 1024.0
            i += 1
        
        if i == 0:  # Bytes
            return f"{int(size)} {size_names[i]}"
        else:
            return f"{size:.1f} {size_names[i]}"
    
    def clear_cache(self):
        self._metadata_cache.clear()


class PathScanner:
    
    DIR_COMMANDS = {'cd', 'pushd', 'popd', 'rmdir'}
    
    FILE_COMMANDS = {'cat', 'less', 'more', 'head', 'tail', 'vim', 'nano', 'code', 'subl', 'gedit'}
    
    BOTH_COMMANDS = {'ls', 'll', 'la', 'cp', 'mv', 'rm', 'chmod', 'chown', 'stat', 'file', 'du', 'find'}
    
    def __init__(self):
        self._cache = {}
        self._cache_time = {}
        self.metadata = FileMetadata()
        
    def _get_cache_key(self, path: str) -> str:
        """Generate cache key for a path"""
        try:
            mtime = os.path.getmtime(path) if os.path.exists(path) else 0
            return f"{path}:{mtime}"
        except OSError:
            return f"{path}:0"
    
    def _is_cache_valid(self, path: str) -> bool:
        cache_key = self._get_cache_key(path)
        return cache_key in self._cache
    
    def scan_directory(self, path: str = None, include_hidden: bool = False) -> Tuple[Dict[str, List[str]], Dict[str, str]]:

        if path is None:
            path = os.getcwd()
            
        cache_key = self._get_cache_key(path)
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        files = []
        directories = []
        meta_dict = {}
        
        try:
            for item in os.listdir(path):
                if not include_hidden and item.startswith('.'):
                    continue
                    
                item_path = os.path.join(path, item)
                
                meta_info = self.metadata.get_file_info(item_path)
                meta_dict[item] = meta_info
                
                if os.path.isdir(item_path):
                    directories.append(item)
                elif os.path.isfile(item_path):
                    files.append(item)
                    
        except (PermissionError, FileNotFoundError):
            pass
        
        result = (
            {
                'files': sorted(files),
                'directories': sorted(directories)
            },
            meta_dict
        )
        
        self._cache[cache_key] = result
        return result
    
    def get_completions_for_command(self, command: str, path: str = None) -> Tuple[List[str], Dict[str, str]]:
        scan_result, meta_dict = self.scan_directory(path)
        
        if command in self.DIR_COMMANDS:
            items = scan_result['directories']
        elif command in self.FILE_COMMANDS:
            items = scan_result['files']
        else:
            items = scan_result['files'] + scan_result['directories']
        
        filtered_meta = {item: meta_dict[item] for item in items if item in meta_dict}
        
        return items, filtered_meta


class CommandParser:
    
    def __init__(self):
        self.scanner = PathScanner()
    
    def parse_input(self, text: str) -> Dict[str, any]:
        """
        Parse input text and return completion context
        Returns: {
            'command': str,
            'args': List[str], 
            'current_arg': str,
            'completion_type': str,  # 'path', 'command', 'none'
            'target_directory': str
        }
        """
        if not text.strip():
            return {
                'command': '',
                'args': [],
                'current_arg': '',
                'completion_type': 'command',
                'target_directory': os.getcwd()
            }
        
        parts = text.split()
        command = parts[0] if parts else ''
        args = parts[1:] if len(parts) > 1 else []
        
        if len(parts) == 1 and not text.endswith(' '):
            completion_type = 'command'
            current_arg = command
        else:
            completion_type = 'path'
            if text.endswith(' '):
                current_arg = ''
            else:
                current_arg = args[-1] if args else ''
        
        target_directory = os.getcwd()
        
        if current_arg and ('/' in current_arg or '\\' in current_arg):
            dir_part = os.path.dirname(current_arg)
            if dir_part:
                potential_dir = os.path.join(os.getcwd(), dir_part)
                if os.path.isdir(potential_dir):
                    target_directory = potential_dir
        
        return {
            'command': command,
            'args': args,
            'current_arg': current_arg,
            'completion_type': completion_type,
            'target_directory': target_directory
        }


class DynamicPathCompleter(Completer):
    
    def __init__(self):
        self.parser = CommandParser()
        self.scanner = PathScanner()
        
        self.shell_commands = [
            'ls', 'cd', 'pwd', 'cat', 'less', 'more', 'head', 'tail',
            'cp', 'mv', 'rm', 'mkdir', 'rmdir', 'chmod', 'chown',
            'find', 'grep', 'awk', 'sed', 'sort', 'uniq', 'wc',
            'ps', 'kill', 'jobs', 'bg', 'fg', 'top', 'htop',
            'vim', 'nano', 'code', 'git', 'python', 'pip','source',
            'clear', 'history', 'exit', 'which', 'whereis'
        ]
        
        self.command_meta = {
            'ls': '📋 List directory contents',
            'cd': '📁 Change directory',
            'pwd': '📍 Print working directory',
            'cat': '📄 Display file contents',
            'less': '📖 View file with paging',
            'more': '📖 View file with paging',
            'head': '⬆️ Display first lines of file',
            'tail': '⬇️ Display last lines of file',
            'cp': '📋 Copy files or directories',
            'mv': '➡️ Move/rename files or directories',
            'rm': '🗑️ Remove files or directories',
            'mkdir': '📁 Create directory',
            'rmdir': '🗂️ Remove empty directory',
            'chmod': '🔐 Change file permissions',
            'chown': '👤 Change file ownership',
            'find': '🔍 Search for files and directories',
            'grep': '🔍 Search text patterns in files',
            'vim': '📝 Vi/Vim text editor',
            'nano': '📝 Nano text editor',
            'code': '💻 VS Code editor',
            'git': '📚 Git version control',
            'python': '🐍 Python interpreter',
            'pip': '📦 Python package installer'
        }
        
    def get_completions(self, document: Document, complete_event):
        text = document.text_before_cursor
        context = self.parser.parse_input(text)
        
        if context['completion_type'] == 'command':
            fuzzy_completer = FuzzyWordCompleter(
                words=self.shell_commands,
                meta_dict=self.command_meta
            )
            
            for completion in fuzzy_completer.get_completions(document, complete_event):
                yield completion
        
        elif context['completion_type'] == 'path':
            command = context['command']
            current_arg = context['current_arg']
            target_dir = context['target_directory']
            
            candidates, meta_dict = self.scanner.get_completions_for_command(command, target_dir)
            
            if candidates:
                if current_arg and ('/' in current_arg or '\\' in current_arg):
                    dir_part = os.path.dirname(current_arg)
                    file_part = os.path.basename(current_arg)
                    
                    filtered_candidates = []
                    filtered_meta = {}
                    
                    for candidate in candidates:
                        if candidate.lower().startswith(file_part.lower()) or self._fuzzy_match(candidate, file_part):
                            filtered_candidates.append(candidate)
                            if candidate in meta_dict:
                                filtered_meta[candidate] = meta_dict[candidate]
                    
                    if filtered_candidates:
                        fuzzy_completer = FuzzyWordCompleter(
                            words=filtered_candidates,
                            meta_dict=filtered_meta
                        )
                        
                        partial_doc = Document(file_part, len(file_part))
                        
                        for completion in fuzzy_completer.get_completions(partial_doc, complete_event):
                            correct_start_position = -len(current_arg) + completion.start_position + len(file_part)
                            
                            if correct_start_position > 0:
                                correct_start_position = -len(current_arg)
                            
                            new_completion = Completion(
                                text=completion.text,
                                start_position=correct_start_position,
                                display=completion.display,
                                display_meta=completion.display_meta
                            )
                            yield new_completion
                else:
                    fuzzy_completer = FuzzyWordCompleter(
                        words=candidates,
                        meta_dict=meta_dict
                    )
                    
                    arg_doc = Document(current_arg, len(current_arg))
                    
                    for completion in fuzzy_completer.get_completions(arg_doc, complete_event):
                        yield completion
    
    def _fuzzy_match(self, candidate: str, query: str) -> bool:
        if not query:
            return True
            
        candidate_lower = candidate.lower()
        query_lower = query.lower()
        
        candidate_idx = 0
        for char in query_lower:
            while candidate_idx < len(candidate_lower) and candidate_lower[candidate_idx] != char:
                candidate_idx += 1
            if candidate_idx >= len(candidate_lower):
                return False
            candidate_idx += 1
        
        return True

class CompletionManager:
    def __init__(self):
        self.path_completer = DynamicPathCompleter()
        
    def get_completer(self):
        return self.path_completer
        
    def update_cache(self, path: str = None):
        if path is None:
            path = os.getcwd()
        
        cache_key = self.path_completer.scanner._get_cache_key(path)
        if cache_key in self.path_completer.scanner._cache:
            del self.path_completer.scanner._cache[cache_key]
            
        self.path_completer.scanner.metadata.clear_cache()
            
    def clear_cache(self):
        self.path_completer.scanner._cache.clear()
        self.path_completer.scanner._cache_time.clear()
        self.path_completer.scanner.metadata.clear_cache()
    
    def refresh_directory(self, path: str = None):
        self.update_cache(path)
        
    def set_show_hidden(self, show_hidden: bool):
        pass


def create_completion_manager() -> CompletionManager:
    return CompletionManager()


def get_file_metadata(file_path: str) -> str:
    metadata = FileMetadata()
    return metadata.get_file_info(file_path)
