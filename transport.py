class SocketTransport(object):
    def __init__(self, sock, loop, addr, protocol_cls):
        self.sock = sock
        self.loop = loop
        self.addr = addr
        self.protocol = protocol_cls()
        self.protocol.set_transport(self)
        self.loop.add_reader(sock, self.read_ready)

    def write(self, data):
        try:
            # 尝试写入数据，可能会因为缓冲区已满导致写入失败
            n = self.sock.send(data)
        except BlockingIOError:
            pass
        else:
            # 可能会没发送完
            data = data[n:]
            if not data:
                self.sock.close()
                return
        # 如果写入失败或没有写完则使用事件监听，可写时再次进行写入
        self.loop.add_writer(self.sock, self.write_ready, data)

    def write_ready(self, data):
        try:
            self.sock.send(data)
        except BlockingIOError:
            pass
        else:
            self.loop.remove_reader(self.sock)

    def read_ready(self):
        data = self.sock.recv(1024)
        # 如果没有数据了，就移除事件监听，减少资源占用
        if not data:
            self.loop.remove_reader(self.sock)
            self.sock.close()
            return
        # 接收完数据， 调用协议层进行数据处理
        self.protocol.data_received(data)
