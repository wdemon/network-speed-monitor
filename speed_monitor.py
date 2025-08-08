import time
from datetime import datetime
from utils import test_speed, save_data, cleanup_old_data, CONFIG

if __name__ == "__main__":
    while True:
        print(f"Testing speed at {datetime.now().strftime('%H:%M')}...")
        data = test_speed()
        if data:
            save_data(data)
            cleanup_old_data()
            print(f"Results: Download={data['download']} Mbps, Upload={data['upload']} Mbps")
        else:
            print("Speed test failed.")

        time.sleep(CONFIG["test_interval"])
