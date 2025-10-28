#!/usr/bin/env python3
"""
cleanup_db.py

Script de nettoyage automatique de la base de données Vocalyx.
Supprime les transcriptions anciennes et libère l'espace disque.
"""

import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import configparser

# Import des modèles depuis app.py
try:
    from sqlalchemy import create_engine, func
    from sqlalchemy.orm import sessionmaker
    from app import Transcription, Base
except ImportError as e:
    print(f"❌ Error importing dependencies: {e}")
    print("Make sure you're running from the vocalyx directory")
    sys.exit(1)


class DatabaseCleaner:
    def __init__(self, config_file="config.ini", dry_run=False):
        self.dry_run = dry_run
        self.config = self._load_config(config_file)
        self.engine = create_engine(
            self.config['database_path'],
            connect_args={"check_same_thread": False}
        )
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
    
    def _load_config(self, config_file):
        """Charge la configuration depuis config.ini"""
        config = configparser.ConfigParser()
        if not Path(config_file).exists():
            print(f"⚠️  Config file not found: {config_file}")
            print("Using default database path")
            return {'database_path': 'sqlite:///./transcriptions.db'}
        
        config.read(config_file)
        return {
            'database_path': config.get('PATHS', 'database_path', 
                                       fallback='sqlite:///./transcriptions.db')
        }
    
    def get_stats(self):
        """Obtient les statistiques de la base de données"""
        total = self.session.query(Transcription).count()
        
        stats = {
            'total': total,
            'pending': self.session.query(Transcription).filter(
                Transcription.status == 'pending'
            ).count(),
            'processing': self.session.query(Transcription).filter(
                Transcription.status == 'processing'
            ).count(),
            'done': self.session.query(Transcription).filter(
                Transcription.status == 'done'
            ).count(),
            'error': self.session.query(Transcription).filter(
                Transcription.status == 'error'
            ).count(),
        }
        
        # Plus ancienne et plus récente
        if total > 0:
            oldest = self.session.query(Transcription).order_by(
                Transcription.created_at.asc()
            ).first()
            newest = self.session.query(Transcription).order_by(
                Transcription.created_at.desc()
            ).first()
            
            stats['oldest_date'] = oldest.created_at
            stats['newest_date'] = newest.created_at
        else:
            stats['oldest_date'] = None
            stats['newest_date'] = None
        
        return stats
    
    def cleanup_old(self, days=30):
        """Supprime les transcriptions plus anciennes que X jours"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        old_entries = self.session.query(Transcription).filter(
            Transcription.created_at < cutoff_date
        ).all()
        
        if not old_entries:
            print(f"✅ No transcriptions older than {days} days")
            return 0
        
        print(f"\n📊 Found {len(old_entries)} transcriptions older than {days} days:")
        
        # Grouper par statut
        by_status = {}
        for entry in old_entries:
            status = entry.status or 'unknown'
            by_status[status] = by_status.get(status, 0) + 1
        
        for status, count in by_status.items():
            print(f"   - {status}: {count}")
        
        if self.dry_run:
            print(f"\n🔍 DRY RUN: Would delete {len(old_entries)} entries")
            return len(old_entries)
        
        # Suppression
        for entry in old_entries:
            self.session.delete(entry)
        
        self.session.commit()
        print(f"\n✅ Deleted {len(old_entries)} old transcriptions")
        return len(old_entries)
    
    def cleanup_by_status(self, status='error'):
        """Supprime les transcriptions par statut"""
        entries = self.session.query(Transcription).filter(
            Transcription.status == status
        ).all()
        
        if not entries:
            print(f"✅ No transcriptions with status '{status}'")
            return 0
        
        print(f"\n📊 Found {len(entries)} transcriptions with status '{status}'")
        
        if self.dry_run:
            print(f"\n🔍 DRY RUN: Would delete {len(entries)} entries")
            return len(entries)
        
        for entry in entries:
            self.session.delete(entry)
        
        self.session.commit()
        print(f"\n✅ Deleted {len(entries)} transcriptions")
        return len(entries)
    
    def cleanup_incomplete(self):
        """Supprime les transcriptions incomplètes (pending/processing depuis >1h)"""
        cutoff_date = datetime.utcnow() - timedelta(hours=1)
        
        entries = self.session.query(Transcription).filter(
            Transcription.status.in_(['pending', 'processing']),
            Transcription.created_at < cutoff_date
        ).all()
        
        if not entries:
            print("✅ No stuck transcriptions")
            return 0
        
        print(f"\n📊 Found {len(entries)} stuck transcriptions:")
        for entry in entries:
            age = datetime.utcnow() - entry.created_at
            print(f"   - {entry.id}: {entry.status} (age: {age})")
        
        if self.dry_run:
            print(f"\n🔍 DRY RUN: Would delete {len(entries)} entries")
            return len(entries)
        
        for entry in entries:
            self.session.delete(entry)
        
        self.session.commit()
        print(f"\n✅ Deleted {len(entries)} stuck transcriptions")
        return len(entries)
    
    def vacuum(self):
        """Optimise la base de données (SQLite VACUUM)"""
        if self.dry_run:
            print("🔍 DRY RUN: Would run VACUUM")
            return
        
        print("\n🔧 Running VACUUM to reclaim space...")
        self.session.execute("VACUUM")
        self.session.commit()
        print("✅ Database optimized")
    
    def print_stats(self):
        """Affiche les statistiques"""
        stats = self.get_stats()
        
        print("\n" + "="*50)
        print("📊 DATABASE STATISTICS")
        print("="*50)
        print(f"\nTotal transcriptions: {stats['total']}")
        print(f"  ⏳ Pending:     {stats['pending']}")
        print(f"  ⚙️  Processing:  {stats['processing']}")
        print(f"  ✅ Done:        {stats['done']}")
        print(f"  ❌ Error:       {stats['error']}")
        
        if stats['oldest_date']:
            print(f"\n📅 Date range:")
            print(f"  Oldest: {stats['oldest_date'].strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  Newest: {stats['newest_date'].strftime('%Y-%m-%d %H:%M:%S')}")
            age = datetime.utcnow() - stats['oldest_date']
            print(f"  Age: {age.days} days")
        
        print("="*50 + "\n")
    
    def close(self):
        """Ferme la session"""
        self.session.close()


def main():
    parser = argparse.ArgumentParser(
        description="Vocalyx Database Cleanup Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Afficher les statistiques
  python cleanup_db.py --stats
  
  # Supprimer les transcriptions > 30 jours
  python cleanup_db.py --days 30
  
  # Supprimer uniquement les erreurs
  python cleanup_db.py --status error
  
  # Supprimer les transcriptions bloquées
  python cleanup_db.py --incomplete
  
  # Tout nettoyer + optimiser
  python cleanup_db.py --days 30 --incomplete --vacuum
  
  # Mode dry-run (simulation)
  python cleanup_db.py --days 30 --dry-run
  
  # Nettoyage agressif
  python cleanup_db.py --days 7 --status error --incomplete --vacuum
        """
    )
    
    parser.add_argument('--config', default='config.ini',
                       help='Path to config file (default: config.ini)')
    parser.add_argument('--stats', action='store_true',
                       help='Show database statistics')
    parser.add_argument('--days', type=int, metavar='N',
                       help='Delete transcriptions older than N days')
    parser.add_argument('--status', choices=['pending', 'processing', 'done', 'error'],
                       help='Delete transcriptions by status')
    parser.add_argument('--incomplete', action='store_true',
                       help='Delete stuck transcriptions (pending/processing > 1h)')
    parser.add_argument('--vacuum', action='store_true',
                       help='Optimize database (reclaim space)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be deleted without actually deleting')
    parser.add_argument('-y', '--yes', action='store_true',
                       help='Skip confirmation prompt')
    
    args = parser.parse_args()
    
    # Au moins une action requise
    if not any([args.stats, args.days, args.status, args.incomplete, args.vacuum]):
        parser.print_help()
        return
    
    print("\n🧹 Vocalyx Database Cleanup Tool")
    print("="*50)
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
        print("="*50)
    
    cleaner = DatabaseCleaner(config_file=args.config, dry_run=args.dry_run)
    
    try:
        # Toujours afficher les stats au début
        cleaner.print_stats()
        
        total_deleted = 0
        
        # Confirmation si pas en dry-run et pas de --yes
        if not args.dry_run and not args.yes and not args.stats:
            response = input("\n⚠️  Continue with cleanup? (y/N): ")
            if response.lower() != 'y':
                print("❌ Cleanup cancelled")
                return
        
        # Cleanup par ancienneté
        if args.days:
            print(f"\n🗓️  Cleaning transcriptions older than {args.days} days...")
            deleted = cleaner.cleanup_old(days=args.days)
            total_deleted += deleted
        
        # Cleanup par statut
        if args.status:
            print(f"\n🔍 Cleaning transcriptions with status '{args.status}'...")
            deleted = cleaner.cleanup_by_status(status=args.status)
            total_deleted += deleted
        
        # Cleanup des bloquées
        if args.incomplete:
            print("\n⏰ Cleaning stuck transcriptions...")
            deleted = cleaner.cleanup_incomplete()
            total_deleted += deleted
        
        # Vacuum
        if args.vacuum and total_deleted > 0:
            cleaner.vacuum()
        
        # Stats finales si nettoyage effectué
        if total_deleted > 0 or args.stats:
            print("\n" + "="*50)
            print("📊 FINAL STATISTICS")
            print("="*50)
            cleaner.print_stats()
            
            if total_deleted > 0:
                print(f"✅ Total deleted: {total_deleted} transcriptions\n")
        
    except KeyboardInterrupt:
        print("\n\n❌ Cleanup interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cleaner.close()


if __name__ == '__main__':
    main()