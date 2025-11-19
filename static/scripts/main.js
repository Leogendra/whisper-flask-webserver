document.addEventListener('DOMContentLoaded', function(){
  const form = document.getElementById('transcribe-form');
  const submitBtn = document.getElementById('submit-btn');
  if(form && submitBtn){
    form.addEventListener('submit', function(){
      submitBtn.disabled = true;
      submitBtn.textContent = 'Transcription en cours...';
    });
  }
});