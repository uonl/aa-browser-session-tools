(function(){
  // 修复 AA 原生「发送后输入框文字未清空」的竞态问题（新会话 + 已有会话都覆盖）。
  // 匹配所有会话输入框（新会话 placeholder="描述任务..."，已有会话="回复，或用新指令中断..."）。
  var LAST_SENT='', TIMER=null, CHECKS=0;
  function textarea(){
    return document.querySelector('textarea[placeholder="描述任务..."],textarea[placeholder="回复，或用新指令中断..."]')
        || document.querySelector('textarea');
  }
  function isWorking(){
    var body=(document.body&&document.body.innerText)||'';
    return /正在工作|Stop generating|正在生成/.test(body);
  }
  function clearIfStale(){
    var ta=textarea();
    if(!ta){LAST_SENT='';return}
    if(LAST_SENT && (ta.value!==LAST_SENT || isWorking())){
      if(ta.value===LAST_SENT){
        var setter=Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set;
        setter.call(ta,'');
        ta.dispatchEvent(new Event('input',{bubbles:true}));
      }
      LAST_SENT='';return;
    }
    CHECKS++;
    if(CHECKS<16){TIMER=setTimeout(clearIfStale,250)}else{LAST_SENT=''} // 最多等 4 秒
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
    var btn=e.target&&e.target.closest&&e.target.closest('button[aria-label="发送"],button[aria-label="发送任务"],button[aria-label*="发送"]');
    if(btn)markSend();
  },true);
})();
