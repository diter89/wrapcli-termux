#!/usr/bin/env python3
import os
import sys
import subprocess
import json
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import psutil
from datetime import datetime


class EnvironmentDetector:
    def __init__(self):
        self._cache = {}
        self._cache_timeout = 5 
        self._last_cache_time = 0
    
    def _should_refresh_cache(self) -> bool:
        import time
        return time.time() - self._last_cache_time > self._cache_timeout
    
    def _update_cache_time(self):
        import time
        self._last_cache_time = time.time()
    
    def get_python_environment(self) -> Optional[Dict[str, str]]:
        if not self._should_refresh_cache() and 'python_env' in self._cache:
            return self._cache['python_env']
        
        env_info = None
        
        if os.environ.get('VIRTUAL_ENV'):
            venv_path = os.environ['VIRTUAL_ENV']
            env_name = os.path.basename(venv_path)
            env_info = {
                'type': 'venv',
                'name': env_name,
                'path': venv_path,
                'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                'display': f"({env_name})"
            }
        
        elif os.environ.get('CONDA_DEFAULT_ENV'):
            conda_env = os.environ['CONDA_DEFAULT_ENV']
            if conda_env != 'base':  
                env_info = {
                    'type': 'conda',
                    'name': conda_env,
                    'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                    'display': f"(conda:{conda_env})"
                }
        
        elif self._is_poetry_project():
            project_name = self._get_poetry_project_name()
            env_info = {
                'type': 'poetry',
                'name': project_name or 'poetry',
                'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                'display': f"(poetry:{project_name or 'project'})"
            }
        
        elif os.environ.get('PIPENV_ACTIVE'):
            pipenv_project = os.path.basename(os.getcwd())
            env_info = {
                'type': 'pipenv',
                'name': pipenv_project,
                'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                'display': f"(pipenv:{pipenv_project})"
            }
        
        self._cache['python_env'] = env_info
        self._update_cache_time()
        return env_info
    
    def get_git_status(self) -> Optional[Dict[str, str]]:

        if not self._should_refresh_cache() and 'git_status' in self._cache:
            return self._cache['git_status']
        
        git_info = None
        
        try:
            subprocess.run(['git', 'rev-parse', '--git-dir'], 
                         capture_output=True, check=True, timeout=2)
            
            branch_result = subprocess.run(['git', 'branch', '--show-current'], 
                                         capture_output=True, text=True, timeout=2)
            
            if branch_result.returncode == 0:
                branch = branch_result.stdout.strip()
                if not branch:
                    commit_result = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], 
                                                 capture_output=True, text=True, timeout=2)
                    branch = f"HEAD@{commit_result.stdout.strip()}"
                
                status_info = self._get_git_status_indicators()
                
                git_info = {
                    'branch': branch,
                    'display': f"git:{branch}",
                    **status_info
                }
        
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        self._cache['git_status'] = git_info
        self._update_cache_time()
        return git_info
    
    def _get_git_status_indicators(self) -> Dict[str, any]:
        try:
            status_result = subprocess.run(['git', 'status', '--porcelain'], 
                                         capture_output=True, text=True, timeout=2)
            
            has_changes = bool(status_result.stdout.strip())
            
            ahead_behind_result = subprocess.run(['git', 'rev-list', '--left-right', '--count', 'HEAD...@{upstream}'], 
                                                capture_output=True, text=True, timeout=2)
            
            ahead, behind = 0, 0
            if ahead_behind_result.returncode == 0:
                parts = ahead_behind_result.stdout.strip().split()
                if len(parts) == 2:
                    ahead, behind = int(parts[0]), int(parts[1])
            
            return {
                'has_changes': has_changes,
                'ahead': ahead,
                'behind': behind,
                'status_symbol': '●' if has_changes else '○'
            }
        
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return {
                'has_changes': False,
                'ahead': 0,
                'behind': 0,
                'status_symbol': '○'
            }
    
    def get_node_environment(self) -> Optional[Dict[str, str]]:
  
        if not self._should_refresh_cache() and 'node_env' in self._cache:
            return self._cache['node_env']
        
        node_info = None
        
        if os.path.exists('package.json'):
            try:
                with open('package.json', 'r') as f:
                    package_data = json.load(f)
                
                project_name = package_data.get('name', 'node-project')
                version = package_data.get('version', '0.0.0')
                
                has_modules = os.path.exists('node_modules')
                
                node_info = {
                    'type': 'node',
                    'name': project_name,
                    'version': version,
                    'has_modules': has_modules,
                    'display': f"node:{project_name}"
                }
            
            except (json.JSONDecodeError, OSError):
                pass
        
        self._cache['node_env'] = node_info
        self._update_cache_time()
        return node_info
    
    def get_docker_status(self) -> Optional[Dict[str, str]]:

        docker_info = None
        
        if os.path.exists('Dockerfile') or os.path.exists('docker-compose.yml'):
            docker_info = {
                'type': 'docker',
                'has_dockerfile': os.path.exists('Dockerfile'),
                'has_compose': os.path.exists('docker-compose.yml'),
                'display': 'docker'
            }
        
        if os.path.exists('/.dockerenv'):
            if docker_info:
                docker_info['inside_container'] = True
            else:
                docker_info = {
                    'type': 'docker',
                    'inside_container': True,
                    'display': 'docker:container'
                }
        
        return docker_info
    
    def get_system_info(self) -> Dict[str, any]:

        try:
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            return {
                'memory_percent': memory.percent,
                'memory_available': memory.available // (1024**2),  # MB
                'cpu_percent': cpu_percent,
                'load_average': os.getloadavg()[0] if hasattr(os, 'getloadavg') else 0,
                'uptime': datetime.now().strftime('%H:%M')
            }
        except:
            return {
                'memory_percent': 0,
                'memory_available': 0,
                'cpu_percent': 0,
                'load_average': 0,
                'uptime': datetime.now().strftime('%H:%M')
            }
    
    def _is_poetry_project(self) -> bool:
        return os.path.exists('pyproject.toml')
    
    def _get_poetry_project_name(self) -> Optional[str]:
        try:
            import tomli
            
            with open('pyproject.toml', 'rb') as f:
                data = tomli.load(f)
            
            return data.get('tool', {}).get('poetry', {}).get('name')
        except:
            return os.path.basename(os.getcwd())
    
    def get_all_environments(self) -> Dict[str, any]:

        return {
            'python': self.get_python_environment(),
            'git': self.get_git_status(),
            'node': self.get_node_environment(),
            'docker': self.get_docker_status(),
            'system': self.get_system_info()
        }
    
    def get_prompt_indicators(self) -> List[Tuple[str, str]]:
        indicators = []
        
        py_env = self.get_python_environment()
        if py_env:
            indicators.append(('class:env_python', py_env['display']))
        
        git_status = self.get_git_status()
        if git_status:
            git_display = f"git:{git_status['branch']}"
            if git_status.get('has_changes'):
                git_display += "●"
            indicators.append(('class:env_git', git_display))
        
        node_env = self.get_node_environment()
        if node_env:
            indicators.append(('class:env_node', node_env['display']))
        
        docker_status = self.get_docker_status()
        if docker_status:
            indicators.append(('class:env_docker', docker_status['display']))
        
        return indicators
    
    def get_status_bar_info(self) -> str:
        system = self.get_system_info()
        git = self.get_git_status()
        py_env = self.get_python_environment()
        
        status_parts = []
        
        if system['cpu_percent'] > 80 or system['memory_percent'] > 85:
            status_parts.append(f"⚠️ CPU:{system['cpu_percent']:.0f}% MEM:{system['memory_percent']:.0f}%")
        else:
            status_parts.append(f"CPU:{system['cpu_percent']:.0f}% MEM:{system['memory_percent']:.0f}%")
        
        if py_env:
            status_parts.append(f"🐍 {py_env['name']}")
        
        if git:
            git_indicator = f"📊 {git['branch']}"
            if git.get('has_changes'):
                git_indicator += "●"
            status_parts.append(git_indicator)
        
        status_parts.append(f"🕒 {system['uptime']}")
        
        return " │ ".join(status_parts)


env_detector = EnvironmentDetector()

def get_python_env():
    """Get Python environment info"""
    return env_detector.get_python_environment()

def get_git_info():
    """Get Git status info"""
    return env_detector.get_git_status()

def get_prompt_env_indicators():
    """Get environment indicators for prompt"""
    return env_detector.get_prompt_indicators()

def get_status_info():
    """Get status bar information"""
    return env_detector.get_status_bar_info()

def get_all_env_info():
    """Get all environment information"""
    return env_detector.get_all_environments()
