import socket
import asyncio

class ECHONETLiteStack:
    """UDP 3610ポートでの通信を管理する"""
    IP_ADDR = "0.0.0.0"
    PORT = 3610
    MULTICAST_GROUP = "224.0.23.0"

    def __init__(self):
        self.transport = None
        self.protocol = None
        self.objects = {} # 0x0288 -> ObjectInstance

    def register_object(self, obj_instance):
        """機器オブジェクト（スマートメーター等）をスタックに登録"""
        self.objects[obj_instance.code] = obj_instance

    async def start(self):
        """UDPサーバーの開始とマルチキャストのジョイン"""
        loop = asyncio.get_running_loop()
        
        # UDPソケットの作成
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.IP_ADDR, self.PORT))

        # マルチキャスト参加設定 (Windows/Linux両対応を考慮)
        mreq = socket.inet_aton(self.MULTICAST_GROUP) + socket.inet_aton(self.IP_ADDR)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        self.transport, self.protocol = await loop.create_datagram_endpoint(
            lambda: ECHONETLiteProtocol(self),
            sock=sock
        )
        print(f"ECHONET Lite Stack started on {self.PORT}/udp")

class ECHONETLiteProtocol(asyncio.DatagramProtocol):
    def __init__(self, stack):
        self.stack = stack

    def datagram_received(self, data, addr):
        """パケットを受信した際の処理"""
        # TODO: フレーム解析 (EHD, TID, SEOJ, DEOJ, ESV, OPC, EPC...)
        print(f"Received {len(data)} bytes from {addr}")
        self.handle_frame(data, addr)

    def handle_frame(self, data, addr):
        # 簡易的なECHONET Lite解析ロジック
        if len(data) < 12: return
        
        ehd1, ehd2 = data[0], data[1]
        if ehd1 != 0x10 or ehd2 != 0x81: return # ECHONET Lite 形式チェック
        
        deoj_cls = data[7] << 8 | data[8]
        deoj_ins = data[9]
        
        # 宛先機器が存在するか確認
        if (deoj_cls, deoj_ins) in self.stack.objects:
            obj = self.stack.objects[(deoj_cls, deoj_ins)]
            obj.process_request(data, addr)
        elif deoj_cls == 0x0EF0: # Node Profile Object
            # TODO: ノードプロファイルへの処理 (機器検索等)
            pass

echonet_stack = ECHONETLiteStack()
 antiviral_software = None # Placeholder for potential library usage
