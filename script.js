document.getElementById('compare-btn').addEventListener('click', async function () {
  const crypto1 = document.getElementById('crypto1').value;
  const crypto2 = document.getElementById('crypto2').value;

  try {
    const response1 = await fetch(`https://api.binance.com/api/v3/ticker/24hr?symbol=${crypto1}`);
    const response2 = await fetch(`https://api.binance.com/api/v3/ticker/24hr?symbol=${crypto2}`);

    const data1 = await response1.json();
    const data2 = await response2.json();

    const marketCapRatio = (data1.quoteVolume / data2.quoteVolume).toFixed(2);

    document.getElementById('crypto-data').textContent = `1 ${crypto1} = ${marketCapRatio} ${crypto2}`;
  } catch (err) {
    document.getElementById('crypto-data').textContent = 'Error fetching data.';
    console.error(err);
  }
});
