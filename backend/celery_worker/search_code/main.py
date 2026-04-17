import os
import sys

# Add src directory to path to allow imports
# sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from src.SearchWorkflow import SearchWorkflow    

if __name__ == "__main__":
    
    # 示例参数
    task_id = "task_033"
    user_query = "糖尿病性视网膜病变(DR厂和糖尿病黄斑水肿(DME)的peripheral retinal biomarkers(周边视网膜标识物)"
    # user_query = "吸烟有害健康"
    outputlanguage = "ru"
    search_settings = {
                        "max_refinement_attempts": 100,
                        "min_study_threshold": 500
                    }
    search_filters = {
            "time": '2000-2026',
            "author": '',
            "first_author": '',
            "last_author": '',
            "affiliation": '',
            "journal": '',
            "custom": ''
        }
    journal_filters = {
            "impact_factor": '',
            "jcr_zone": 'q1-q4',
            "cas_zone": '1-4'
        }

    # 创建搜索工作流实例
    workflow = SearchWorkflow(
        task_id=task_id,
        user_id="user_001",
        user_query=user_query,
        output_language=outputlanguage,
        search_settings=search_settings,
        search_filters=search_filters,
        journal_filters=journal_filters
    )