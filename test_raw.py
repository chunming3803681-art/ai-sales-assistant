import socket

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("127.0.0.1", 9999))
s.listen(1)
print("裸 socket 服务器在 http://127.0.0.1:9999")
print("打开浏览器测试...")

conn, addr = s.accept()
print(f"收到连接: {addr}")
response = b"HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: 19\r\nConnection: close\r\n\r\n<h1>Hello World!</h1>"
conn.sendall(response)
print(f"已发送 {len(response)} 字节")
conn.close()
s.close()
print("完成")