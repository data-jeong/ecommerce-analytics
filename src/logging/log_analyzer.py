from elasticsearch import Elasticsearch
from datetime import datetime, timedelta
import pandas as pd
import logging
from typing import Dict, List, Optional
import json
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LogAnalyzer:
    def __init__(self):
        self.es = Elasticsearch(['http://localhost:9200'])
        self.report_path = Path("reports/log_analysis")
        self.report_path.mkdir(parents=True, exist_ok=True)
        
    def query_logs(self, 
                   index: str,
                   start_time: datetime,
                   end_time: datetime,
                   size: int = 10000) -> List[Dict]:
        """Elasticsearch에서 로그를 쿼리합니다."""
        query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "range": {
                                "timestamp": {
                                    "gte": start_time.isoformat(),
                                    "lt": end_time.isoformat()
                                }
                            }
                        }
                    ]
                }
            },
            "sort": [
                {"timestamp": {"order": "asc"}}
            ],
            "size": size
        }
        
        response = self.es.search(index=index, body=query)
        return [hit["_source"] for hit in response["hits"]["hits"]]
    
    def analyze_error_patterns(self, 
                             start_time: datetime,
                             end_time: datetime) -> pd.DataFrame:
        """에러 패턴을 분석합니다."""
        logs = self.query_logs("order_logs", start_time, end_time)
        
        error_logs = [
            log for log in logs 
            if "error" in log.get("level", "").lower() or 
               "exception" in str(log.get("message", "")).lower()
        ]
        
        if not error_logs:
            return pd.DataFrame()
        
        error_df = pd.DataFrame(error_logs)
        
        # 에러 타입별 집계
        error_patterns = error_df.groupby("error_type").agg({
            "timestamp": "count",
            "message": lambda x: list(set(x))[:3]  # 대표적인 에러 메시지 3개
        }).rename(columns={"timestamp": "count"})
        
        return error_patterns
    
    def analyze_performance_metrics(self,
                                  start_time: datetime,
                                  end_time: datetime) -> pd.DataFrame:
        """성능 메트릭을 분석합니다."""
        logs = self.query_logs("order_logs", start_time, end_time)
        
        if not logs:
            return pd.DataFrame()
        
        perf_df = pd.DataFrame(logs)
        perf_df["timestamp"] = pd.to_datetime(perf_df["timestamp"])
        
        # 시간별 성능 메트릭 집계
        hourly_metrics = perf_df.set_index("timestamp").resample("1H").agg({
            "response_time": ["mean", "max", "min", "count"],
            "memory_usage": "mean",
            "cpu_usage": "mean"
        })
        
        return hourly_metrics
    
    def analyze_user_activity(self,
                            start_time: datetime,
                            end_time: datetime) -> pd.DataFrame:
        """사용자 활동을 분석합니다."""
        logs = self.query_logs("order_logs", start_time, end_time)
        
        if not logs:
            return pd.DataFrame()
        
        activity_df = pd.DataFrame(logs)
        activity_df["timestamp"] = pd.to_datetime(activity_df["timestamp"])
        
        # 시간별 사용자 활동 집계
        hourly_activity = activity_df.set_index("timestamp").resample("1H").agg({
            "user_id": "nunique",
            "event_type": "count",
            "session_id": "nunique"
        }).rename(columns={
            "user_id": "unique_users",
            "event_type": "total_events",
            "session_id": "unique_sessions"
        })
        
        return hourly_activity
    
    def analyze_system_health(self,
                            start_time: datetime,
                            end_time: datetime) -> Dict:
        """시스템 건강 상태를 분석합니다."""
        logs = self.query_logs("order_logs", start_time, end_time)
        
        if not logs:
            return {}
        
        health_df = pd.DataFrame(logs)
        
        # 에러율 계산
        total_requests = len(health_df)
        error_requests = len(health_df[health_df["status_code"] >= 400])
        error_rate = error_requests / total_requests if total_requests > 0 else 0
        
        # 응답 시간 분석
        response_times = pd.to_numeric(health_df["response_time"], errors="coerce")
        
        return {
            "error_rate": error_rate,
            "avg_response_time": response_times.mean(),
            "p95_response_time": response_times.quantile(0.95),
            "p99_response_time": response_times.quantile(0.99),
            "success_rate": 1 - error_rate,
            "total_requests": total_requests
        }
    
    def generate_daily_report(self, date: Optional[datetime] = None):
        """일일 로그 분석 리포트를 생성합니다."""
        if date is None:
            date = datetime.now() - timedelta(days=1)
            
        start_time = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(days=1)
        
        logger.info(f"Generating log analysis report for {date.date()}")
        
        # 각 분석 실행
        error_patterns = self.analyze_error_patterns(start_time, end_time)
        performance_metrics = self.analyze_performance_metrics(start_time, end_time)
        user_activity = self.analyze_user_activity(start_time, end_time)
        system_health = self.analyze_system_health(start_time, end_time)
        
        # 리포트 저장
        report = {
            "date": date.date().isoformat(),
            "error_patterns": error_patterns.to_dict(),
            "performance_metrics": performance_metrics.to_dict(),
            "user_activity": user_activity.to_dict(),
            "system_health": system_health
        }
        
        report_file = self.report_path / f"log_report_{date.date()}.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)
            
        logger.info(f"Log analysis report saved to {report_file}")
        
        return report
    
    def analyze_trends(self, days: int = 7):
        """최근 N일간의 트렌드를 분석합니다."""
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        logger.info(f"Analyzing trends for the last {days} days")
        
        # 일별 시스템 건강 상태 수집
        daily_health = []
        current_date = start_time
        
        while current_date < end_time:
            next_date = current_date + timedelta(days=1)
            health = self.analyze_system_health(current_date, next_date)
            health["date"] = current_date.date().isoformat()
            daily_health.append(health)
            current_date = next_date
            
        # 트렌드 분석
        health_df = pd.DataFrame(daily_health)
        
        trends = {
            "error_rate_trend": health_df["error_rate"].tolist(),
            "response_time_trend": health_df["avg_response_time"].tolist(),
            "request_volume_trend": health_df["total_requests"].tolist(),
            "dates": health_df["date"].tolist()
        }
        
        # 트렌드 리포트 저장
        trend_file = self.report_path / f"trend_report_{end_time.date()}.json"
        with open(trend_file, "w") as f:
            json.dump(trends, f, indent=2)
            
        logger.info(f"Trend analysis report saved to {trend_file}")
        
        return trends

if __name__ == "__main__":
    analyzer = LogAnalyzer()
    
    # 어제의 일일 리포트 생성
    yesterday = datetime.now() - timedelta(days=1)
    analyzer.generate_daily_report(yesterday)
    
    # 최근 7일간의 트렌드 분석
    analyzer.analyze_trends(days=7) 