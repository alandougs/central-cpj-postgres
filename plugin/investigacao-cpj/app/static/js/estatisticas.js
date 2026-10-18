// ---------------- estatísticas

$("#b-ir-export").onclick=()=>{abrirAba("sistema");$("#b-exportar").scrollIntoView({behavior:"smooth"})};
{
 const hoje=new Date(),ano=hoje.getFullYear(),mes=String(hoje.getMonth()+1).padStart(2,"0");
 $("#prod-inicio").value=`${ano}-${mes}-01`;
 $("#prod-fim").value=`${ano}-${mes}-${String(hoje.getDate()).padStart(2,"0")}`;
 $("#f-producao").onsubmit=e=>{if($("#prod-inicio").value>$("#prod-fim").value){e.preventDefault();toast("O início do período deve ser anterior ou igual ao fim.")}};
}



