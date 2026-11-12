import base64
r='/workspace/outputs/cyber_louvre/'
t=open(r+'src/web_template.html').read()
g=base64.b64encode(open(r+'web/model_web.glb','rb').read()).decode()
open(r+'web/preview.html','w').write(t.replace('__GLB_BASE64__',g))
print(len(t)+len(g))
