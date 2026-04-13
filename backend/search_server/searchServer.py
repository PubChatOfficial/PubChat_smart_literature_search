import os
import json
import logging
import asyncpg
from quart import Quart, request, jsonify
from celery import Celery
from common_utils.logger import setup_logging
# Correcting the import based on file content. 
# If require_session_id was intended, it should probably be require_session or aliased.
# Using require_session as alias to match the decorator usage if the previous code used it, 
# but simply importing require_session is safer if we update usage.
# from common_utils.auth_middleware import require_session

setup_logging('search_server')

# Initialize Logger
logger = logging.getLogger(__name__)

# Initialize Quart App
app = Quart(__name__)

# Celery Configuration
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL')
celery_app = Celery('search_tasks', broker=CELERY_BROKER_URL)

# Database Connection Config
DB_CONFIG = {
    "database": os.getenv("POSTGRES_DB"),
    "user": os.getenv("POSTGRES_USER"), 
    "password": os.getenv("POSTGRES_PASSWORD"),
    "host": os.getenv("POSTGRES_HOST"),
    "port": os.getenv("POSTGRES_PORT")
}

@app.route('/health', methods=['GET'])
async def health_check():
    logger.info("Health check requested.")
    return jsonify({"status": "literature-search service is running!"}), 200

@app.route('/task', methods=['POST'])
async def create_search_task():
    logger.info("Search requested.")
    # user_id = g.user_id
    data = await request.get_json()
    
    conn = None
    redis_client = None
    try:
        conn = await asyncpg.connect(**DB_CONFIG)
        async with conn.transaction():
            # 1. Atomic check for user status
            # Use ROW SHARE or FOR UPDATE to lock the user row
            # user_row = await conn.fetchrow(
            #     'SELECT available_times, is_running FROM "userSchema"."users" WHERE id = $1 FOR UPDATE', 
            #     user_id
            # )
            
            # if not user_row:
            #     return jsonify({
            #         "success": False,
            #         "message": {"zh": "用户不存在", "en": "User not found"}
            #     }), 404
                
            # if user_row['is_running']:
            #     return jsonify({
            #         "success": False,
            #         "message": {"zh": "当前有任务正在运行，请稍后重试", "en": "Task is running, please try again later"}
            #     }), 400 # Too Many Requests? Or 400.
            
            # # if user_row['available_times'] <= 0:
            # #     return jsonify({
            # #         "success": False,
            # #         "message": {"zh": "余额已用完", "en": "Balance exhausted"}
            # #     }), 403
            
            # # 2. Update user status to running
            # # Note: We do NOT decrement times here, as per logic "submit task". 
            # # Usually times are decremented on finish or start. 
            # # Assuming just marking as running for now.
            # await conn.execute('UPDATE "userSchema"."users" SET is_running = true WHERE id = $1', user_id)
            
            # 3. Create Task Record
            # Extract fields from nested structures
            s_settings = data.get('search_settings', {})
            s_filters = data.get('search_filters', {})
            j_filters = data.get('journal_filters', {})
            ai_filters = data.get('llm_config', {})

            insert_query = """
                INSERT INTO "userSchema"."tasks" (
                    output_language, user_query,
                    max_refinement_attempts, min_study_threshold,
                    time, author, first_author, last_author, affiliation, journal, custom,
                    impact_factor, jcr_zone, cas_zone, model, api
                ) VALUES (
                    $1, $2, $3,
                    $4, $5,
                    $6, $7, $8, $9, $10, $11, $12,
                    $13, $14, $15, $16
                ) RETURNING id
            """
            
            task_id = await conn.fetchval(
                insert_query,
                data.get('outputlanguage'),
                data.get('user_query'),
                # Search Settings
                s_settings.get('max_refinement_attempts'),
                s_settings.get('min_study_threshold'),
                # Search Filters
                s_filters.get('time'),
                s_filters.get('author'),
                s_filters.get('first_author'),
                s_filters.get('last_author'),
                s_filters.get('affiliation'),
                s_filters.get('journal'),
                s_filters.get('custom'),
                # Journal Filters
                j_filters.get('impact_factor'),
                j_filters.get('jcr_zone'),
                j_filters.get('cas_zone'),
                # LLM Config
                ai_filters.get('model'),
                ai_filters.get('api'),
            )
            
            # 4. Push to Celery
            # We send the task_id. The worker will likely need to fetch the task from DB or we pass parameters.
            # Passing just ID is cleaner if worker has DB access.
            async_result = celery_app.send_task('search_workflow.run_search', args=[str(task_id)], queue='search_queue')
            celery_task_id = async_result.id

            # Store celery_task_id in Redis with 30m expiration
            import redis.asyncio as redis
            redis_client = redis.Redis(host=os.getenv("REDIS_HOST", "redis"), port=6379, db=0, decode_responses=True)
            await redis_client.setex(f"task:{str(task_id)}:celery_id", 1800, celery_task_id)
            
            # Set initial status to Pending
            await redis_client.hset(f"task:{str(task_id)}:info", "status", "Pending")
            await redis_client.expire(f"task:{str(task_id)}:info", 1800)

        return jsonify({
            "success": True,
            "message": {"zh": "任务已提交", "en": "Task submitted"},
            "data": {"search_task_id": str(task_id)}
        }), 200

    except Exception as e:
        logger.error(f"Error creating search task: {e}")
        return jsonify({
            "success": False,
            "message": {"zh": f"任务创建失败，原因为：{e}", "en": f"Failed to create task, reason: {e}"}
        }), 500
    finally:
        if conn:
            await conn.close()
        if redis_client:
            await redis_client.aclose()

@app.route('/task/stop', methods=['POST'])
async def stop_search_task():
    logger.info("Stop task requested.")
    # user_id = g.user_id
    data = await request.get_json()
    task_id = data.get('task_id')
    
    if not task_id:
        return jsonify({"success": False, "message": {"zh": "缺少任务ID", "en": "Missing task ID"}}), 400

    conn = None
    redis_client = None
    try:
        import redis.asyncio as redis
        redis_client = redis.Redis(host=os.getenv("REDIS_HOST", "redis"), port=6379, db=0, decode_responses=True)
        
        # Get celery_task_id from Redis
        celery_task_id = await redis_client.get(f"task:{task_id}:celery_id")
        
        # 1. Revoke the Celery task
        revoke_id = celery_task_id if celery_task_id else task_id
        celery_app.control.revoke(revoke_id, terminate=True)
        logger.info(f"Task {task_id} (Celery ID: {revoke_id}) revoked.")
        
        # # 2. Update User Status in DB and Task Status
        # conn = await asyncpg.connect(**DB_CONFIG)
        # await conn.execute('UPDATE "userSchema"."users" SET is_running = false WHERE id = $1', user_id)
        
        # Update tasks table status if column exists
        try:
            # Assuming 'status' column exists, if not this will fail but caught
             await conn.execute('UPDATE "userSchema"."tasks" SET status = \'stopped\' WHERE id = $1', int(task_id))
        except Exception as e:
            logger.warning(f"Could not update status in tasks table (maybe column missing?): {e}")

        # 3. Update Redis status to "Stopped" so frontend reflects it
        await redis_client.hset(f"task:{task_id}:info", "status", "Stopped")

        return jsonify({"success": True, "message": {"zh": "任务已停止", "en": "Task stopped"}}), 200

    except Exception as e:
        logger.error(f"Failed to stop task: {e}")
        return jsonify({"success": False, "message": {"zh": f"停止任务失败: {e}", "en": f"Failed to stop task: {e}"}}), 500
    finally:
        if conn:
            await conn.close()
        if redis_client:
            await redis_client.aclose()

@app.route('/search_status/<string:task_id>', methods=['GET'])
async def get_search_status(task_id):
    logger.info(f"Checking status for task: {task_id}")
    import redis.asyncio as redis
    
    redis_client = None
    try:
        redis_client = redis.Redis(host=os.getenv("REDIS_HOST", "redis"), port=6379, db=0, decode_responses=True)
        
        info_key = f"task:{task_id}:info"
        retrieval_key = f"task:{task_id}:retrieval"
        articles_key = f"task:{task_id}:articles"

        # 1. 获取基本信息 (Status, Progress)
        info = await redis_client.hgetall(info_key)
        if not info:
             # Redis 中没有，可能任务太久了或ID错误。
            return jsonify({
                "success": False,
                "message": {"zh": "任务不存在或已过期", "en": "Task not found or expired"}
            }), 404

        status = info.get("status", "Pending")
        progress_json = info.get("progress", "{}")
        search_progress = json.loads(progress_json) if progress_json else {}

        # 2. 获取列表数据 (Retrieval, Articles)
        retrieval_list_raw = await redis_client.lrange(retrieval_key, 0, -1)
        articles_list_raw = await redis_client.lrange(articles_key, 0, -1)
        
        retrieval = [json.loads(item) for item in retrieval_list_raw]
        output_review = [json.loads(item) for item in articles_list_raw]

        # 3. 构造返回结构
        response_data = {
            "success": True,
            "status_code": 200,
            "message": {
                "en": "Status retrieved",
                "zh": "状态已获取"
            },
            "data": {
                "search_status": status,
                "download_link": info.get("download_link"),
                "retrieval": retrieval,
                "search_progress": search_progress,
                "output_review": output_review
            }
        }
        
        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f"Error fetching search status: {e}")
        return jsonify({
            "success": False,
            "message": {"zh": f"获取状态失败: {e}", "en": f"Failed to get status: {e}"}
        }), 500
    finally:
        if redis_client:
            await redis_client.aclose()


@app.route('/documents', methods=['GET'])
async def get_user_documents():
    """Get list of generated documents for the user"""
    # user_id = g.user_id
    
    conn = None
    try:
        conn = await asyncpg.connect(**DB_CONFIG)
        # Fetch documents ordered by created_time desc
        rows = await conn.fetch("""
            SELECT *
            FROM "userSchema"."documents" 
            ORDER BY created_time DESC
        """)
        
        # Convert to list of dicts
        documents = []
        for row in rows:
            # Handle potential Decimal type for size
            size_val = row['size']
            if hasattr(size_val, 'real'): # Check if number
                size_val = float(size_val)
                
            # Handle created_time potentially being a string already (depending on driver/DB)
            created_time_val = row['created_time']
            if created_time_val and hasattr(created_time_val, 'isoformat'):
                created_time_str = created_time_val.isoformat()
            else:
                created_time_str = str(created_time_val) if created_time_val else None

            documents.append({
                "id": str(row['id']),
                "task_id": str(row['task_id']) if row['task_id'] else None,
                "size": size_val,
                "user_query": row['user_query'],
                "created_time": created_time_str,
                "download_link": row['download_link']
            })
            
        return jsonify({
            "success": True,
            "data": documents
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to fetch documents: {e}")
        return jsonify({
            "success": False, 
            "message": {"zh": "获取文档列表失败", "en": "Failed to fetch documents"}
        }), 500
    finally:
        if conn:
            await conn.close()


@app.route('/documents/<string:doc_id>', methods=['DELETE'])
async def delete_document(doc_id):
    """Delete a document"""
    # user_id = g.user_id
    
    conn = None
    try:
        conn = await asyncpg.connect(**DB_CONFIG)
        
        # Verify ownership and existence
        # row = await conn.fetchrow(
        #     'SELECT user_query, download_link FROM "userSchema"."documents" WHERE id = $1::uuid',
        #     doc_id
        # )
        
        # if not row:
        #     return jsonify({
        #         "success": False,
        #         "message": {"zh": "文档不存在或无权删除", "en": "Document not found or permission denied"}
        #     }), 404
            
        # Delete from DB
        await conn.execute(
            'DELETE FROM "userSchema"."documents" WHERE id = $1::uuid',
            doc_id
        )
        return jsonify({
            "success": True, 
            "message": {"zh": "文档已删除", "en": "Document deleted"}
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to delete document: {e}")
        return jsonify({
            "success": False, 
            "message": {"zh": f"删除文档失败: {e}", "en": "Failed to delete document"}
        }), 500
    finally:
        if conn:
            await conn.close()

