#서버 목록(IP/ 계정명 / 패스워드)
$servers = @(
 #   @{ ip = "192.168.1.1"; username = "root"; password = '1'}, 
    @{ ip = "172.18.62.212"; username = "root"; password = '1'}
)

#SSH 명령어
$command = @"
    tar -cvpzf /tmp/Linux_Scan_Result.tar.gz /lib /lib64 /bin /sbin /var /usr /etc /boot /opt --exclude=/var/log --exclude=/var/cache --exclude=/var/tmp 
"@

#PS1 안쓸시 .sh로 쓸 명령어
#tar -cvpzf /tmp/Linux_$(hostname -I | awk '{print $1}').tar.gz /lib /lib64 /bin /sbin /var /usr /etc /boot /opt --exclude=/var/log --exclude=/var/cache --exclude=/var/tmp 

#각 서버에 명령어 전송
foreach ($server in $servers) {
    $ip = $server.ip
    $username = $server.username
    $password = $server.password
    $remoteFilePath = "/tmp/Linux_Scan_Result.tar.gz" #리눅스 아카이브 파일 경로
    $LocalFilePath = ".\Linux_Result_${ip}.tar.gz"

    #Plink를 이용한 아카이브 실행
    & .\plink.exe -ssh -batch $username@$ip -pw $password $command
    #PSCP를 이용한 결과파일 복사
    & .\pscp.exe -pw $password "$username@${ip}:${remoteFilePath}" $LocalFilePath
    #Plink를 이용하여 결과파일 제거 (rm -rf 불가한 곳을 위한 echo y 사용)
    & .\plink.exe -ssh -batch $username@$ip -pw $password "echo y | rm ${remoteFilePath}"

    #성공 메시지 출력
    Write-Host "Command sent complete to $ip"
}