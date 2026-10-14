let tc=0,nCiclo=0;async function ciclo(){clearTimeout(tc);if(!S.usuario)return;nCiclo++;try{await atualizarTarefas();if($("#nova").classList.contains("on")||$("#inicio").classList.contains("on"))await atualizarFila();if($("#pendencias").classList.contains("on"))await carregarPendencias();if(casoAberto)await atualizarIA();

 if(nCiclo%3===0&&$("#sistema").classList.contains("on"))await carregarAgentes()}catch(e){}tc=setTimeout(ciclo,1600)}



