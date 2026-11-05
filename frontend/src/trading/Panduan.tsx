export function PanduanPasar() {
  return (
    <article className="panel guide-body pasar-guide">
      <h2>Cara main Kilas Pasar</h2>
      <p>
        Kamu dilempar ke satu titik di masa lalu pada chart pasar <b>asli</b> (kripto, saham IDX, atau saham US). Candle berikutnya belum terlihat;
        kamu memutuskan beli atau jual, lalu memajukan waktu candle demi candle. Semua data masa depan tetap di server, jadi tidak bisa diintip.
      </p>
      <h3>Mode</h3>
      <ul>
        <li><b>Main sendiri</b>: atur pasar, timeframe, modal, dan fee sendiri. Waktu maju kalau kamu menekan tombol (atau diputar otomatis).</li>
        <li><b>Tantangan harian</b>: semua pemain mendapat potongan chart yang sama, 150 candle. Percobaan pertama masuk papan peringkat.</li>
        <li><b>Balapan</b>: main bareng teman di satu room. Candle maju otomatis untuk semua orang, return tertinggi menang.</li>
      </ul>
      <h3>Mode buta</h3>
      <p>
        Nama aset, tanggal, dan level harga disamarkan (harga dikali satu angka acak, jadi persentase gerakannya tetap sama persis).
        Sumbu waktu menampilkan <code>H+3 14:00</code> artinya hari ke-3 sejak sesi dimulai. Identitas asli dibuka di layar hasil.
      </p>
      <h3>Order (spot)</h3>
      <ul>
        <li><b>Market</b>: langsung terisi di harga terakhir, ditambah slippage.</li>
        <li><b>Limit beli</b>: beli saat harga turun ke harga yang kamu pasang. <b>Limit jual</b>: jual saat harga naik ke harga itu (take profit).</li>
        <li><b>Stop beli</b>: beli saat harga menembus ke atas (breakout). <b>Stop jual</b>: jual saat harga turun ke harga itu (stop loss). Stop terisi sebagai order market, jadi kena slippage.</li>
        <li><b>SL/TP</b> yang diisi bersama order beli aktif setelah order beli terisi, sebagai pasangan OCO: kalau salah satu terisi, yang lain batal.</li>
        <li>Spot berarti tidak bisa short dan tidak ada leverage: kamu hanya bisa menjual aset yang dimiliki. Untuk short dan leverage, pilih produk <b>Futures</b> atau <b>Margin + short</b>.</li>
      </ul>
      <h3>Produk per pasar</h3>
      <table>
        <thead><tr><th>Pasar</th><th>Spot</th><th>Futures</th><th>Margin + short</th></tr></thead>
        <tbody>
          <tr><td>Kripto</td><td>Ya</td><td>Ya (perpetual USDⓈ-M ala Binance)</td><td>–</td></tr>
          <tr><td>Saham US</td><td>Ya</td><td>Hanya aturan bebas</td><td>Ya (Reg T, short semua saham)</td></tr>
          <tr><td>Saham IDX</td><td>Ya</td><td>Hanya aturan bebas</td><td>Ya (short hanya ASII, BBCA, BRPT, BUMI, INDF)</td></tr>
        </tbody>
      </table>
      <p className="hint">"Aturan bebas" membuka short dan futures untuk semua saham. Berguna untuk latihan, tapi tidak seperti pasar aslinya.</p>
      <h3>Futures perpetual (kripto)</h3>
      <ul>
        <li><b>Long</b> untung saat harga naik, <b>short</b> untung saat harga turun. Satu posisi bersih per sesi (one-way): jual saat long berarti mengurangi/menutup, lalu kelebihannya jadi short.</li>
        <li><b>Leverage</b> 1–125× tergantung aset dan besar posisi (tabel tier). Margin awal = nilai posisi ÷ leverage.</li>
        <li><b>Cross</b>: seluruh saldo menahan posisi. <b>Isolated</b>: hanya margin posisi yang bisa hilang; margin bisa ditambah/dikurangi.</li>
        <li><b>Likuidasi</b> terjadi saat margin balance turun ke maintenance margin (margin ratio 100%). Posisi ditutup di harga likuidasi dan sisa margin posisi masuk dana asuransi. Garis oranye di chart = harga likuidasi.</li>
        <li><b>Fee</b>: maker 0,02% untuk limit yang menunggu, taker 0,05% untuk market, stop, dan limit yang langsung terisi. <b>Post-only</b> menolak limit yang akan langsung terisi.</li>
        <li><b>Funding</b> tiap 00:00, 08:00, 16:00 UTC: rate positif → long membayar short (dan sebaliknya), sebesar nilai posisi × rate. Memakai data funding asli Binance kalau sudah diunduh, kalau belum 0,01% per 8 jam.</li>
        <li>Order: Limit, Market, Stop (jadi market saat harga picu tersentuh), Stop-limit (jadi limit saat harga picu tersentuh), opsi <b>reduce-only</b>, dan TP/SL yang menempel di posisi.</li>
      </ul>
      <h3>Margin + short (saham)</h3>
      <ul>
        <li><b>US (Reg T)</b>: daya beli 2×, maintenance 25% long / 30% short, langsung dilikuidasi kalau di bawahnya. Komisi USD 0,005/lembar (min USD 1), plus SEC fee dan FINRA TAF saat menjual. Bunga margin ±5,12%/tahun, pinjam saham ±0,25%/tahun.</li>
        <li><b>IDX (BEI)</b>: short hanya untuk Daftar Efek Short Selling, jaminan awal minimal Rp50 juta, margin call di rasio jaminan 135%, forced buy di 120%. Buka short wajib order limit di harga ≥ harga terakhir (uptick). Margin long 2×, forced sell saat ekuitas 20% dari nilai posisi. Bunga 18%/tahun dihitung harian.</li>
        <li>Bunga dan biaya pinjam dipotong tiap pergantian hari kalender (termasuk akhir pekan). Kas negatif = dana pinjaman dari broker.</li>
      </ul>
      <h3>Backtest strategi sendiri</h3>
      <p>
        Tab <b>Backtest</b> menguji strategi yang kamu tulis sebagai file Python di folder <code>strategi/</code> pada data historis
        semua aset (per aset atau sebagai portofolio), dengan fee, funding, bunga, dan aturan short yang sama seperti di atas.
        Keputusan dibuat saat candle ditutup dan dieksekusi di candle berikutnya. Panduan lengkap ada di <code>strategi/README.md</code>.
      </p>
      <h3>Bagaimana order dieksekusi</h3>
      <p>
        Order diperiksa pada candle <b>dasar</b> (timeframe terkecil yang tersedia untuk sesi itu, misalnya 1 menit untuk kripto) walaupun chart yang
        kamu lihat 4 jam. Di dalam satu candle, harga diasumsikan bergerak: candle naik O → Low → High → Close, candle turun O → High → Low → Close.
        Kalau harga membuka melewati harga order (gap), order terisi di harga open.
      </p>
      <h3>Fee default</h3>
      <table>
        <thead><tr><th>Pasar</th><th>Beli</th><th>Jual</th><th>Catatan</th></tr></thead>
        <tbody>
          <tr><td>Kripto</td><td>0,10%</td><td>0,10%</td><td>Satuan koin, boleh pecahan</td></tr>
          <tr><td>Saham IDX</td><td>0,15%</td><td>0,25%</td><td>Termasuk PPh final 0,1% saat jual. 1 lot = 100 lembar</td></tr>
          <tr><td>Saham US</td><td>0,05%</td><td>0,05%</td><td>Satuan lembar</td></tr>
        </tbody>
      </table>
      <p className="hint">Fee, bunga, leverage awal, dan slippage bisa diubah di mode Main sendiri. Angka default adalah perkiraan (dicek November 2026), bukan angka resmi broker tertentu, dan aturan bursa bisa berubah.</p>
      <h3>Data</h3>
      <ul>
        <li>Kripto: arsip publik Binance, candle 1 menit sejak 2017. Timeframe lain dihitung dari data 1 menit. Mode Futures memakai harga spot sebagai harga acuan.</li>
        <li>Saham: Yahoo Finance. Harian tersedia puluhan tahun; 1 jam ±2 tahun; 5–30 menit ±60 hari; 1 menit ±30 hari.
          Jalankan perintah update secara rutin supaya data intraday saham makin panjang.</li>
        <li>Harga saham sudah disesuaikan dengan stock split, tapi belum memperhitungkan dividen.</li>
      </ul>
      <p className="hint">Semua uang di game ini virtual. Ini alat latihan membaca chart, bukan saran investasi.</p>
    </article>
  );
}
