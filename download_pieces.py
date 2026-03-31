import os
import requests

card_dir = './assets/card'
piece_dir = './assets/broadcastGeneral'
os.makedirs(piece_dir, exist_ok=True)
filenames = [f for f in os.listdir(card_dir) if f.endswith('.png')]

base_url = 'https://web.sanguosha.com/10/pc/res/assets/runtime/tavernChess/broadcastGeneral/'

for name in filenames:
    url = base_url + name
    save_path = os.path.join(piece_dir, name)
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            with open(save_path, 'wb') as f:
                f.write(resp.content)
            print(f"Downloaded: {name}")
        else:
            print(f"Failed: {name} (status {resp.status_code})")
    except Exception as e:
        print(f"Error: {name} ({e})")


