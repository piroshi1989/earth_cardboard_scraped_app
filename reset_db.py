import logging
from database import Database

logging.basicConfig(level=logging.INFO)

def reset_database():
    """データベースのテーブルを再作成"""
    try:
        db = Database()
        
        # テーブルの削除と再作成
        logging.info("テーブルの再作成を開始します...")
        db.drop_tables()
        db._create_tables()
        logging.info("テーブルの再作成が完了しました")
        
    except Exception as e:
        logging.error(f"データベースのリセット中にエラーが発生: {str(e)}")
        raise