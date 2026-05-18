PowerShell’i proje kökünde aç:

cd C:\Users\HP\Desktop\Projeler\Bitirme
Görünür terminallerle, eski bağlantıları/task state’i düşürerek güvenli yeniden başlat:

.\scripts\local_nodes_visible_supervisor.ps1 -Action restart -Node all -StopExisting
Durumu kontrol et:

.\scripts\local_nodes_visible_supervisor.ps1 -Action status -Node all
Sadece orchestrator restart:

.\scripts\local_nodes_visible_supervisor.ps1 -Action restart -Node orchestrator -StopExisting
Sadece crawler restart:

.\scripts\local_nodes_visible_supervisor.ps1 -Action restart -Node crawler -StopExisting
İkisini durdur:

.\scripts\local_nodes_visible_supervisor.ps1 -Action stop -Node all
Logları izlemek için:

Get-Content $env:USERPROFILE\orchestrator.log -Wait
Get-Content $env:USERPROFILE\crawler.log -Wait
Panel:

http://127.0.0.1:8088
Not: Bu script iki görünür PowerShell penceresi açar. Orchestrator veya crawler düşerse aynı pencere içinde otomatik yeniden başlatır.




