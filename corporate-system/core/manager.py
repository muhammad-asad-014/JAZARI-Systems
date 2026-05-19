import os
import importlib.util
import json
from flask import Flask, Blueprint

class PluginManager:
    def __init__(self, app=None, plugin_folder='plugins'):
        self.app = app
        self.plugin_folder = plugin_folder
        self.plugins = {} 

    def load_plugins(self):
        if not os.path.exists(self.plugin_folder):
            os.makedirs(self.plugin_folder)
        for folder in os.listdir(self.plugin_folder):
            path = os.path.join(self.plugin_folder, folder)
            
            if os.path.isdir(path) and not folder.startswith('__'):
                self._load_single_plugin(folder, path)

    def _load_single_plugin(self, folder_name, path):
        try:
            with open(os.path.join(path, 'manifest.json'), 'r') as f:
                info = json.load(f)

            module_name = f"plugins.{folder_name}"
            init_path = os.path.join(path, "__init__.py")
            
            spec = importlib.util.spec_from_file_location(module_name, init_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if hasattr(module, 'bp'):
                self.app.register_blueprint(module.bp, url_prefix=f"/{info['id']}")
                self.plugins[info['id']] = info
                print(f"Successfully loaded plugin: {info['name']}")

        except Exception as e:
            print(f"Failed to load plugin {folder_name}: {e}")

