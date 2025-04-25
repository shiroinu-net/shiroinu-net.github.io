// textmorphing.js
document.addEventListener('DOMContentLoaded', () => {
    // --- 時間によるテキスト変更ロジックのみ ---
    function updateDynamicTexts() {
      const now = new Date();
      const h = now.getHours(), m = now.getMinutes();
      const nameEl   = document.querySelector('.word.changeName');
      const comingEl = document.querySelector('.word.changeComingText');
  
      if (nameEl) {
        let txt = '';
        if (h >= 15 && h < 16)         txt = '名古屋Orchest-Lab';
        else if (h >= 16 && h < 17)    txt = '化ける身';
        else if (h >= 17 && h < 18)    txt = 'Rishao';
        else if (h === 18 && m < 15)   txt = 'the MusicVideo';
        else if (h > 18 || (h === 18 && m >= 15)) txt = 'thank you';
        if (nameEl.textContent !== txt) nameEl.textContent = txt;
      }
  
      if (comingEl) {
        let txt = 'Coming up next..';
        if (h === 18 && m < 15)        txt = 'about';
        else if (h > 18 || (h === 18 && m >= 15)) txt = '';
        if (comingEl.textContent !== txt) comingEl.textContent = txt;
      }
    }
  
    updateDynamicTexts();
    setInterval(updateDynamicTexts, 60_000);
  });
