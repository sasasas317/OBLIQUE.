// Защищаем опасные действия подтверждением и автоматически убираем уведомления.
document.querySelectorAll('[data-confirm]').forEach(form=>form.addEventListener('submit',e=>{if(!window.confirm(form.dataset.confirm))e.preventDefault()}));setTimeout(()=>document.querySelectorAll('.flash').forEach(x=>x.remove()),4500);
// Дашборд передаёт числа через data-values; SVG строится без графической библиотеки.
const chart=document.querySelector('.chart');if(chart){const values=chart.dataset.values.split(',').map(Number),max=Math.max(1,...values),points=values.map((v,i)=>`${i*10},${100-v/max*90}`).join(' ');chart.innerHTML=`<svg viewBox="0 0 290 110" role="img" aria-label="Выручка по дням"><polyline fill="none" stroke="#641f2d" stroke-width="2" points="${points}"/></svg>`;}
