"""
Health check views for monitoring system status.
"""

from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from app.mongodb import MongoDBConnection
import time


@csrf_exempt
@require_http_methods(["GET"])
def health_check(request):
    """
    Health check endpoint to verify system status.
    Returns the status of PostgreSQL, MongoDB, and overall system health.
    """
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "services": {}
    }
    
    overall_healthy = True
    
    # Check PostgreSQL connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        health_status["services"]["postgresql"] = {
            "status": "healthy",
            "message": "Connection successful"
        }
    except Exception as e:
        overall_healthy = False
        health_status["services"]["postgresql"] = {
            "status": "unhealthy",
            "message": f"Connection failed: {str(e)}"
        }
    
    # Check MongoDB connection
    try:
        mongo_conn = MongoDBConnection()
        db = mongo_conn.get_db()
        # Ping the database
        db.command("ping")
        health_status["services"]["mongodb"] = {
            "status": "healthy",
            "message": "Connection successful"
        }
    except Exception as e:
        overall_healthy = False
        health_status["services"]["mongodb"] = {
            "status": "unhealthy",
            "message": f"Connection failed: {str(e)}"
        }
    
    # Update overall status
    if not overall_healthy:
        health_status["status"] = "unhealthy"
    
    # Return appropriate HTTP status code
    status_code = 200 if overall_healthy else 503
    
    return JsonResponse(health_status, status=status_code)


@csrf_exempt
@require_http_methods(["GET"])
def ready_check(request):
    """
    Readiness check endpoint for Kubernetes/container orchestration.
    Simpler check that just returns 200 if the service is running.
    """
    return JsonResponse({
        "status": "ready",
        "timestamp": time.time()
    })


@csrf_exempt
@require_http_methods(["GET"])
def live_check(request):
    """
    Liveness check endpoint for Kubernetes/container orchestration.
    Returns 200 if the process is alive.
    """
    return JsonResponse({
        "status": "alive",
        "timestamp": time.time()
    })
