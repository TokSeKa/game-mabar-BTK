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
        <li>Spot berarti tidak bisa short dan tidak ada leverage: kamu hanya bisa menjual aset yang dimiliki.</li>
      </ul>
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
      <p className="hint">Fee dan slippage bisa diubah di mode Main sendiri. Angka default adalah perkiraan, bukan angka resmi broker tertentu.</p>
      <h3>Data</h3>
      <ul>
        <li>Kripto: arsip publik Binance, candle 1 menit sejak 2017. Timeframe lain dihitung dari data 1 menit.</li>
        <li>Saham: Yahoo Finance. Harian tersedia puluhan tahun; 1 jam ±2 tahun; 5–30 menit ±60 hari; 1 menit ±30 hari.
          Jalankan perintah update secara rutin supaya data intraday saham makin panjang.</li>
        <li>Harga saham sudah disesuaikan dengan stock split, tapi belum memperhitungkan dividen.</li>
      </ul>
      <p className="hint">Semua uang di game ini virtual. Ini alat latihan membaca chart, bukan saran investasi.</p>
    </article>
  );
}
