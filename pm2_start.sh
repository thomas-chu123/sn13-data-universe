pm2 delete sn13-miner
pm2 start python --name sn13-miner -- ./neurons/miner.py --axon.port 10022 --wallet.name skynet --wallet.hotkey skynet
