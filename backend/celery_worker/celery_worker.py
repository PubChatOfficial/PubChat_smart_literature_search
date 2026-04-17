import os
import logging
import time
from celery import Celery
import psycopg2
from psycopg2.extras import RealDictCursor
from .search_code.src.SearchWorkflow import SearchWorkflow
# If common_utils is needed by SearchWorkflow (it imports logger), it should be in path.
# setup_logging is called in SearchWorkflow imports.

# Setup logging
# Logging is configured by Celery
logger = logging.getLogger(__name__)

# Config
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL')
# Database Connection Config
DB_CONFIG = {
    "database": os.getenv("POSTGRES_DB"),
    "user": os.getenv("POSTGRES_USER"), 
    "password": os.getenv("POSTGRES_PASSWORD"),
    "host": os.getenv("POSTGRES_HOST"),
    "port": os.getenv("POSTGRES_PORT")
}

celery_app = Celery('search_workflow', broker=CELERY_BROKER_URL)
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],  
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    worker_prefetch_multiplier=1
)

@celery_app.task(name='search_workflow.run_search', queue='search_queue')
def run_search(task_id):
    logger.info(f"Received search task: {task_id}")
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        # user_id = None
        task = None
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SELECT * FROM "userSchema"."tasks" WHERE id = %s', (task_id,))
            task = cur.fetchone()
            
            if not task:
                logger.error(f"Task {task_id} not found")
                return
            
            # user_id = task['user_id']
            
            # Handle max_rounds and auto_stop_articles
            max_rounds = 50 if task.get('max_refinement_attempts', 5) > 50 else task.get('max_refinement_attempts', 5)
            auto_stop_articles = 500 if task.get('min_study_threshold', 20) > 500 else task.get('min_study_threshold', 20)
            
            # Reconstruct filters from DB
            search_settings = {
                "max_refinement_attempts": max_rounds,
                "min_study_threshold": auto_stop_articles
            }
            
            search_filters = {
                "time": task.get('time', ''),
                "author": task.get('author', ''),
                "first_author": task.get('first_author', ''),
                "last_author": task.get('last_author', ''),
                "affiliation": task.get('affiliation', ''),
                "journal": task.get('journal', ''),
                "custom": task.get('custom', '')
            }
            
            journal_filters = {
                "impact_factor": task.get('impact_factor', ''),
                "jcr_zone": task.get('jcr_zone', ''),
                "cas_zone": task.get('cas_zone', '')
            }

            llm_config = {
                "model": task.get('model', ''),
                "api": task.get('api', '')
            }

            # Update status to running
            cur.execute("UPDATE \"userSchema\".\"tasks\" SET status = 'running' WHERE id = %s", (task_id,))
            conn.commit()

        # Run Workflow
        logger.info(f"Initializing workflow for task {task_id}")
        try:
             # SearchWorkflow runs in __init__ currently
             workflow = SearchWorkflow(
                task_id=str(task_id),
                user_query=task['user_query'],
                output_language=task['output_language'],
                llm_config=llm_config,
                search_settings=search_settings,
                search_filters=search_filters,
                journal_filters=journal_filters,
                
            )
             
             logger.info(f"Workflow completed for {task_id}")
             
            #  with conn.cursor() as cur:
            #      cur.execute("UPDATE \"userSchema\".\"tasks\" SET status = 'completed' WHERE id = %s", (task_id,))
            #      cur.execute("UPDATE \"userSchema\".\"users\" SET is_running = false WHERE id = %s", (user_id,))
            #      conn.commit()
                 
        except Exception as wf_error:
            logger.error(f"Workflow execution failed: {wf_error}", exc_info=True)
            with conn.cursor() as cur:
                 cur.execute("UPDATE \"userSchema\".\"tasks\" SET status = 'failed' WHERE id = %s", (task_id,))
                #  if user_id:
                #      cur.execute("UPDATE \"userSchema\".\"users\" SET is_running = false WHERE id = %s", (user_id,))
                 conn.commit()
            raise wf_error

    except Exception as e:
        logger.error(f"Task wrapper failed: {e}")
        # Try to reset user status
        # if conn and user_id:
        #     try:
        #         with conn.cursor() as cur:
        #              cur.execute("UPDATE \"userSchema\".\"users\" SET is_running = false WHERE id = %s", (user_id,))
        #              conn.commit()
        #     except:
        #         pass
    finally:
        if conn:
            conn.close()
