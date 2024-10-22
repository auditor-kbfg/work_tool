#���� ���(IP/ ������ / �н�����)
$servers = @(
 #   @{ ip = "192.168.1.1"; username = "root"; password = '1'}, 
    @{ ip = "172.18.62.212"; username = "root"; password = '1'}
)

#SSH ��ɾ�
$command = @"
    tar -cvpzf /tmp/Linux_Scan_Result.tar.gz /lib /lib64 /bin /sbin /var /usr /etc /boot /opt --exclude=/var/log --exclude=/var/cache --exclude=/var/tmp 
"@

#PS1 �Ⱦ��� .sh�� �� ��ɾ�
#tar -cvpzf /tmp/Linux_$(hostname -I | awk '{print $1}').tar.gz /lib /lib64 /bin /sbin /var /usr /etc /boot /opt --exclude=/var/log --exclude=/var/cache --exclude=/var/tmp 

#�� ������ ��ɾ� ����
foreach ($server in $servers) {
    $ip = $server.ip
    $username = $server.username
    $password = $server.password
    $remoteFilePath = "/tmp/Linux_Scan_Result.tar.gz" #������ ��ī�̺� ���� ���
    $LocalFilePath = ".\Linux_Result_${ip}.tar.gz"

    #Plink�� �̿��� ��ī�̺� ����
    & .\plink.exe -ssh -batch $username@$ip -pw $password $command
    #PSCP�� �̿��� ������� ����
    & .\pscp.exe -pw $password "$username@${ip}:${remoteFilePath}" $LocalFilePath
    #Plink�� �̿��Ͽ� ������� ���� (rm -rf �Ұ��� ���� ���� echo y ���)
    & .\plink.exe -ssh -batch $username@$ip -pw $password "echo y | rm ${remoteFilePath}"

    #���� �޽��� ���
    Write-Host "Command sent complete to $ip"
}