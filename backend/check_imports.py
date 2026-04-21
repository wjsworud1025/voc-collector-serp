import sys
sys.path.insert(0, 'C:/Users/admin/Desktop/Cowork_Project/voc-collector/backend')

try:
    import market_config
    print("market_config: OK")
except Exception as e:
    print(f"market_config ERROR: {e}")

try:
    from agent import planner
    print("agent.planner: OK")
except Exception as e:
    print(f"agent.planner ERROR: {e}")

try:
    from routers import reports
    print("routers.reports: OK")
except Exception as e:
    print(f"routers.reports ERROR: {e}")

try:
    import main
    print("main: OK")
except Exception as e:
    print(f"main ERROR: {e}")
