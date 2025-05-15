#!/bin/bash

echo "🔧 Copying service file"
sudo cp /home/mindware/webroster-bio/setup/webroster-bio-ui.service /etc/systemd/system/
sudo cp /home/mindware/webroster-bio/setup/webroster-sync.service /etc/systemd/system/

sudo systemctl daemon-reexec
sudo systemctl enable webroster-bio-ui.service
sudo systemctl enable webroster-sync.service

echo "🐍 Creating Python virtual environment..."
cd /home/mindware/webroster-bio
python3 -m venv venv
source venv/bin/activate

echo "📦 Installing Python packages in venv..."
pip install --upgrade pip
pip install pygame requests Pillow

echo "🛠️ Setting permissions..."
chmod +x start.sh

if [ ! -d "/home/mindware/LCD-show" ]; then
    echo "🖼️ Installing LCD driver..."
    cd /home/mindware
    git clone https://github.com/goodtft/LCD-show.git
    cd LCD-show
    chmod +x LCD35-show
    sudo ./LCD35-show
else
    echo "✅ LCD driver already installed."
fi

echo "🔊 Forcing 3.5mm audio"
amixer cset numid=3 1

sudo systemctl start webroster-bio-ui.service
sudo systemctl start webroster-sync.service
echo "🔄 Reloading systemd...