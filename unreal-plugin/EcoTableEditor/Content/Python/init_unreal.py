# Runs automatically when the editor starts (any Content/Python/init_unreal.py does).
import unreal

try:
    import eco_table_bridge
    eco_table_bridge.start()
except Exception as e:  # never block editor startup
    unreal.log_warning('[EcoTableBridge] failed to start: %s' % e)
