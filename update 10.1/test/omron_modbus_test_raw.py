import serial
 # シリアルポート設定

ser = serial.Serial(

    port='/dev/ttyACM0',  # 実際のデバイス名に変更

    baudrate=9600,

    bytesize=serial.EIGHTBITS,

    parity=serial.PARITY_EVEN,

    stopbits=serial.STOPBITS_ONE,

    timeout=1

)


# Modbus RTUコマンド（バイナリ）

command = bytes.fromhex('010300000002C40B')


# 送信

print("Sending:", command.hex().upper())

ser.write(command)


# 応答受信

response = ser.read(256)  # 最大256バイト読み取り

print("Received:", response.hex().upper())


ser.close() 
