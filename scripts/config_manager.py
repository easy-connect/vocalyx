#!/usr/bin/env python3
"""
config_manager.py

Utilitaire en ligne de commande pour gérer la configuration Vocalyx
"""

import sys
import configparser
import argparse
from pathlib import Path


class ConfigManager:
    def __init__(self, config_file="config.ini"):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        
        if not Path(config_file).exists():
            print(f"❌ Config file not found: {config_file}")
            sys.exit(1)
        
        self.config.read(config_file)
    
    def show(self, section=None):
        """Affiche la configuration"""
        if section:
            if section not in self.config:
                print(f"❌ Section not found: {section}")
                return
            print(f"\n[{section}]")
            for key, value in self.config[section].items():
                print(f"{key} = {value}")
        else:
            for section in self.config.sections():
                print(f"\n[{section}]")
                for key, value in self.config[section].items():
                    print(f"{key} = {value}")
    
    def get(self, section, key):
        """Obtient une valeur"""
        try:
            value = self.config.get(section, key)
            print(f"{section}.{key} = {value}")
        except (configparser.NoSectionError, configparser.NoOptionError):
            print(f"❌ Key not found: {section}.{key}")
    
    def set(self, section, key, value):
        """Modifie une valeur"""
        if section not in self.config:
            print(f"❌ Section not found: {section}")
            return
        
        self.config.set(section, key, value)
        with open(self.config_file, 'w') as f:
            self.config.write(f)
        print(f"✅ Updated: {section}.{key} = {value}")
    
    def validate(self):
        """Valide la configuration"""
        errors = []
        warnings = []
        
        # Vérifier les sections requises
        required_sections = ['WHISPER', 'PERFORMANCE', 'LIMITS', 'PATHS', 'VAD']
        for section in required_sections:
            if section not in self.config:
                errors.append(f"Missing section: {section}")
        
        # Vérifier WHISPER
        if 'WHISPER' in self.config:
            model = self.config.get('WHISPER', 'model', fallback='')
            valid_models = ['tiny', 'base', 'small', 'medium', 'large', 'large-v2', 'large-v3']
            if model not in valid_models:
                errors.append(f"Invalid model: {model}. Must be one of {valid_models}")
            
            device = self.config.get('WHISPER', 'device', fallback='')
            if device not in ['cpu', 'cuda', 'auto']:
                errors.append(f"Invalid device: {device}. Must be cpu, cuda, or auto")
            
            compute_type = self.config.get('WHISPER', 'compute_type', fallback='')
            if compute_type not in ['int8', 'int8_float16', 'float16', 'float32']:
                errors.append(f"Invalid compute_type: {compute_type}")
        
        # Vérifier PERFORMANCE
        if 'PERFORMANCE' in self.config:
            max_workers = self.config.getint('PERFORMANCE', 'max_workers', fallback=0)
            if max_workers < 1 or max_workers > 16:
                warnings.append(f"max_workers={max_workers} may not be optimal. Recommended: 2-8")
            
            segment_length = self.config.getint('PERFORMANCE', 'segment_length_ms', fallback=0)
            if segment_length < 10000 or segment_length > 120000:
                warnings.append(f"segment_length_ms={segment_length} may cause issues. Recommended: 30000-90000")
            
            beam_size = self.config.getint('PERFORMANCE', 'beam_size', fallback=0)
            if beam_size < 1 or beam_size > 10:
                warnings.append(f"beam_size={beam_size} may not be optimal. Recommended: 3-7")
        
        # Vérifier LIMITS
        if 'LIMITS' in self.config:
            max_size = self.config.getint('LIMITS', 'max_file_size_mb', fallback=0)
            if max_size > 500:
                warnings.append(f"max_file_size_mb={max_size} is very high. Consider lowering it.")
        
        # Vérifier PATHS
        if 'PATHS' in self.config:
            upload_dir = Path(self.config.get('PATHS', 'upload_dir', fallback=''))
            if not upload_dir.exists():
                warnings.append(f"Upload directory does not exist: {upload_dir}")
        
        # Afficher les résultats
        if errors:
            print("\n❌ ERRORS:")
            for error in errors:
                print(f"  - {error}")
        
        if warnings:
            print("\n⚠️  WARNINGS:")
            for warning in warnings:
                print(f"  - {warning}")
        
        if not errors and not warnings:
            print("\n✅ Configuration is valid!")
        
        return len(errors) == 0
    
    def preset(self, preset_name):
        """Applique un preset de configuration"""
        presets = {
            'speed': {
                'WHISPER': {'model': 'tiny'},
                'PERFORMANCE': {
                    'max_workers': '8',
                    'segment_length_ms': '45000',
                    'beam_size': '3',
                    'temperature': '0.0'
                },
                'VAD': {'silence_thresh': '-35'}
            },
            'balanced': {
                'WHISPER': {'model': 'small'},
                'PERFORMANCE': {
                    'max_workers': '4',
                    'segment_length_ms': '60000',
                    'beam_size': '5',
                    'temperature': '0.0'
                },
                'VAD': {'silence_thresh': '-40'}
            },
            'accuracy': {
                'WHISPER': {'model': 'medium'},
                'PERFORMANCE': {
                    'max_workers': '2',
                    'segment_length_ms': '90000',
                    'beam_size': '10',
                    'temperature': '0.2'
                },
                'VAD': {'silence_thresh': '-45'}
            }
        }
        
        if preset_name not in presets:
            print(f"❌ Unknown preset: {preset_name}")
            print(f"Available presets: {', '.join(presets.keys())}")
            return
        
        preset = presets[preset_name]
        for section, values in preset.items():
            for key, value in values.items():
                self.config.set(section, key, value)
        
        with open(self.config_file, 'w') as f:
            self.config.write(f)
        
        print(f"✅ Applied preset: {preset_name}")
        print("\nNew configuration:")
        self.show()


def main():
    parser = argparse.ArgumentParser(
        description="Vocalyx Configuration Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Afficher toute la configuration
  python config_manager.py show
  
  # Afficher une section
  python config_manager.py show --section WHISPER
  
  # Obtenir une valeur
  python config_manager.py get WHISPER model
  
  # Modifier une valeur
  python config_manager.py set WHISPER model medium
  
  # Valider la configuration
  python config_manager.py validate
  
  # Appliquer un preset
  python config_manager.py preset speed
  python config_manager.py preset balanced
  python config_manager.py preset accuracy
        """
    )
    
    parser.add_argument('--config', default='config.ini', help='Config file path')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # show
    show_parser = subparsers.add_parser('show', help='Show configuration')
    show_parser.add_argument('--section', help='Show only this section')
    
    # get
    get_parser = subparsers.add_parser('get', help='Get a value')
    get_parser.add_argument('section', help='Section name')
    get_parser.add_argument('key', help='Key name')
    
    # set
    set_parser = subparsers.add_parser('set', help='Set a value')
    set_parser.add_argument('section', help='Section name')
    set_parser.add_argument('key', help='Key name')
    set_parser.add_argument('value', help='New value')
    
    # validate
    subparsers.add_parser('validate', help='Validate configuration')
    
    # preset
    preset_parser = subparsers.add_parser('preset', help='Apply a preset')
    preset_parser.add_argument('name', choices=['speed', 'balanced', 'accuracy'],
                               help='Preset name')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    manager = ConfigManager(args.config)
    
    if args.command == 'show':
        manager.show(args.section if hasattr(args, 'section') else None)
    elif args.command == 'get':
        manager.get(args.section, args.key)
    elif args.command == 'set':
        manager.set(args.section, args.key, args.value)
    elif args.command == 'validate':
        manager.validate()
    elif args.command == 'preset':
        manager.preset(args.name)


if __name__ == '__main__':
    main()