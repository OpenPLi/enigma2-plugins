# -*- coding: utf-8 -*-
from Components.config import config, ConfigSelection, ConfigSubsection, ConfigYesNo

try:
    from Components.config import configfile
except ImportError:
    configfile = None

NAME = "TURKSAT TKGS"
MENU_NAME = "Turksat TKGS"
AUTHOR = "Murat SEVER"
HANDLE = "@muratsevercom"
VERSION = "4.4.8"
WEEKDAYS = ("Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar")

BEACONS = (
    (12380, "V", 27500),
    (12423, "V", 27500),
    (12423, "H", 30000),
    (12458, "V", 30000),
)


def beacon_key(beacon):
    return "%d%s%d" % beacon


def beacon_label(beacon):
    return "%d %s %d" % beacon


config.plugins.mstkgs = ConfigSubsection()
opts = config.plugins.mstkgs
opts.beacon = ConfigSelection(default="auto", choices=[("auto", "Otomatik (%d frekans sırayla)" % len(BEACONS))] + [
    (beacon_key(b), "%d. %s" % (i + 1, beacon_label(b))) for i, b in enumerate(BEACONS)])
opts.order = ConfigSelection(default="HD", choices=[("HD", "HD listesi"), ("SD", "SD listesi")])
opts.numbering = ConfigYesNo(default=True)
opts.top = ConfigYesNo(default=True)
opts.title = ConfigSelection(default="TKGS", choices=[
    ("TKGS", "TKGS"), ("Türksat TKGS", "Türksat TKGS"), ("TKGS Kanallar", "TKGS Kanallar"),
    ("TURKSAT TKGS", "TURKSAT TKGS")])
opts.radio = ConfigYesNo(default=True)
opts.genres = ConfigYesNo(default=False)
opts.scrambled = ConfigYesNo(default=True)
opts.backup = ConfigYesNo(default=True)
opts.patience = ConfigSelection(default="60", choices=[
    ("45", "45 saniye"), ("60", "60 saniye"), ("90", "90 saniye"), ("120", "120 saniye")])
opts.feed = ConfigSelection(default="normal", choices=[
    ("fast", "Çok hızlı"), ("normal", "Hızlı"), ("slow", "Sakin"), ("off", "Kapalı")])
opts.mainmenu = ConfigYesNo(default=False)
opts.diag = ConfigYesNo(default=False)
opts.auto = ConfigSelection(default="off", choices=[
    ("off", "Kapalı"), ("daily", "Her gün"), ("weekly", "Her hafta"), ("monthly", "Her ay")])
opts.auto_time = ConfigSelection(default="04:00", choices=[
    ("%02d:%02d" % (h, m), "%02d:%02d" % (h, m)) for h in range(24) for m in (0, 30)])
opts.auto_day = ConfigSelection(default="0", choices=[(str(i), name) for i, name in enumerate(WEEKDAYS)])
opts.auto_date = ConfigSelection(default="1", choices=[(str(d), "Ayın %d. günü" % d) for d in range(1, 29)])
opts.auto_standby = ConfigYesNo(default=True)
opts.auto_changed = ConfigYesNo(default=True)
opts.auto_notify = ConfigYesNo(default=True)

FIELDS = (
    ("TKGS transponderı", "beacon",
     "Otomatik: 12380 V, 12423 V, 12423 H, 12458 V sırayla denenir (PID 8181). "
     "Çanağınız yalnızca birini alıyorsa sabitleyin."),
    ("Kanal listesi", "order", "TKGS'nin yayınladığı HD veya SD sıralama listesi. HD, Türksat'ın varsayılan önerisidir."),
    ("TKGS kanal numaraları", "numbering",
     "Açık: kanal numaraları TKGS ile birebir aynı olur, boşluklar yer tutucuyla doldurulur."),
    ("Buketi en başa koy", "top", "Numaralandırma açıksa buket her zaman listenin en başına yerleşir."),
    ("Buket adı", "title", "Kanal listesinde görünecek TKGS buket adı."),
    ("Radyo buketi", "radio", "TKGS'deki radyo kanalları için ayrı bir radyo buketi oluşturur."),
    ("Kategori buketleri", "genres", "Haber, Spor, Çocuk gibi TKGS kategorileri için ayrı buketler oluşturur."),
    ("Şifreli kanalları dahil et", "scrambled", "Kapalı: şifreli kanallar bukete yazılmaz, kanal gezgininde HARİÇ görünür."),
    ("Kurulum öncesi yedek al", "backup", "Önceki kanal listesi saklanır; Yönetim ekranından tek tuşla geri dönülür."),
    ("En uzun okuma süresi", "patience", "Zayıf sinyalde tablonun tamamı için daha uzun bekler. Normalde 15-30 sn yeterlidir."),
    ("Kanal akışı", "feed", "Okunan kanalların ekrana birer birer dökülme hızı."),
    ("Ana menüde göster", "mainmenu", "Eklentiyi ana menüye ekler. Enigma2 yeniden başlatıldıktan sonra geçerlidir."),
    ("Tanı kaydı", "diag",
     "Açık: kutu, imaj, Python, tuner ve demux bilgileriyle her adım /home/root/logs/mstkgs_tani.log "
     "dosyasına yazılır. Sorun bildirirken bu dosyayı gönderin. Rapor ekranında sarı tuşla görüntülenir."),
)


AUTO_FIELDS = (
    ("Otomatik güncelleme", "auto",
     "Önerilen: Her gün, bekleme modunda, yalnızca değişiklik varsa. Türksat listeyi sık değiştirmez; "
     "günlük kontrol birkaç saniye sürer ve değişiklik yoksa hiçbir dosyaya dokunulmaz."),
    ("Saat", "auto_time", "Kontrolün yapılacağı saat. Kutu o saatte kapalıysa açıldığında ilk fırsatta yapılır."),
    ("Haftanın günü", "auto_day", "Haftalık kontrolün yapılacağı gün."),
    ("Ayın günü", "auto_date", "Aylık kontrolün yapılacağı gün."),
    ("Yalnızca bekleme modunda", "auto_standby",
     "Açık: izlediğiniz yayın asla kesilmez; kontrol kutu bekleme modundayken yapılır. "
     "Kapalı: boş tuner varsa yayını bölmeden arka planda yapılır."),
    ("Yalnızca liste değiştiyse kur", "auto_changed",
     "Açık: TKGS sürümü son kurulumla aynıysa hiçbir şey yazılmaz. Kapalı: her seferinde yeniden kurulur."),
    ("Bildirim göster", "auto_notify", "Güncelleme sonucunu ekranda kısa bir bildirimle gösterir."),
)


def persist():
    try:
        opts.save()
    except Exception:
        pass
    for saver in (getattr(configfile, "save", None), getattr(config, "save", None)):
        if saver is None:
            continue
        try:
            saver()
            return
        except Exception:
            continue
