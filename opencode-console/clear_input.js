(function(){
  // 修复 AA 原生「发送后输入框文字未清空」的竞态问题。
  // 只在确认发送成功（出现停止按钮/正在工作，或输入框已被 AA 清空）后才兜底清空，
  // 避免发送失败时误清掉用户想重试的文字。
  var LAST_SENT='', TIMER=null, CHECKS=0;
  function textarea(){return document.querySelector('textarea[placeholder="描述任务..."]')}
  function isWorking(){
    // 发送中/工作中的标志：aria-label 含“停止”的按钮，或文本含“正在工作/Stop”
    var stop=document.querySelector('button[aria-label*="停止"],button[aria-label*="停止生成"]');
    if(stop)return true;
    var body=(document.body&&document.body.innerText)||'';
    return /正在工作|Stop generating|正在生成/.test(body);
  }
  function clearIfStale(){
    var ta=textarea();
    if(!ta){LAST_SENT='';return}
    // 若 AA 已自己清空，或检测到正在工作 → 兜底清空（用原生 setter 同步 React 状态）
    if(LAST_SENT && (ta.value!==LAST_SENT || isWorking())){
      if(ta.value===LAST_SENT){
        var setter=Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set;
        setter.call(ta,'');
        ta.dispatchEvent(new Event('input',{bubbles:true}));
      }
      LAST_SENT='';return;
    }
    CHECKS++;
    if(CHECKS<12){TIMER=setTimeout(clearIfStale,250)}else{LAST_SENT=''} // 最多等 3 秒
  }
  function markSend(){
    var ta=textarea();
    if(ta&&ta.value.trim()){LAST_SENT=ta.value;CHECKS=0;clearTimeout(TIMER);TIMER=setTimeout(clearIfStale,300)}
  }
  document.addEventListener('keydown',function(e){
    if(e.key!=='Enter'||e.shiftKey||e.isComposing)return;
    var ta=textarea();
    if(ta&&document.activeElement===ta&&ta.value.trim())markSend();
  },true);
  document.addEventListener('click',function(e){
    var btn=e.target&&e.target.closest&&e.target.closest('button[aria-label="发送任务"],button[aria-label*="发送"]');
    if(btn)markSend();
  },true);
})();
