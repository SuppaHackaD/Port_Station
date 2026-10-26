"""Apply bounded lifetime logging or a pinned context-owned resource cleanup.

Mesa retains its original copyright and licence headers. Added diagnostics:
Copyright 2026 Port Station contributors, SPDX-License-Identifier: MIT.
"""
from pathlib import Path
import hashlib,json

PINNED = {
 'src/gallium/frontends/wgl/stw_context.c':'ccbd510b60b0c5730dfb88909624236f0fb599441eb7fcbcc6f9c50113e7d3b5',
 'src/gallium/frontends/wgl/stw_framebuffer.c':'3d665c84b1140055c1122bcae807f0a57f4c669fe47bdf0af6325a2be28ce66d',
 'src/gallium/frontends/wgl/stw_st.c':'1fdb0384df0280013d9a2ea0bd889fe0165c22e6008c9b7b6274ddfa553b1a9b',
 'src/gallium/drivers/zink/zink_resource.c':'f75d2111cd39a6864c4b1799516d7b78c007dfcdfde907a38aff8e18480724fc',
 'src/gallium/drivers/zink/zink_kopper.c':'f815a4a0cb2a853ccc5d83820679e1ad8187054f89f0ba34c7f674d7f2cbe715',
 'src/gallium/drivers/zink/zink_context.c':'75a14ded04d9d8e3aaf5b482fae9da20a841c7b51a1b4dd14d5bf6031a7abcbf',
 'src/gallium/auxiliary/util/u_inlines.h':'2646f611e8f2666ab177f8f03d3d9e6f208891e1c72efae76aedb8df81302277',
}

# Keep the original reference helper intact. This wrapper evaluates each argument
# once and records counts before the call, since old_dst may be freed by it.
REFERENCE_TRACE = r'''
/* STATION_MESA_REF_BEGIN */
static inline void
station_resource_reference(struct pipe_resource **dst, struct pipe_resource *src,
                           const char *file, int line, const char *function)
{
   struct pipe_resource *old_dst = *dst;
   if (old_dst != src &&
       ((old_dst && (old_dst->bind & PIPE_BIND_DISPLAY_TARGET)) ||
        (src && (src->bind & PIPE_BIND_DISPLAY_TARGET)))) {
      fprintf(stderr, "STATION_MESA resource_ref slot=%p old=%p old_refs=%lld src=%p src_refs=%lld file=%s line=%d func=%s\n",
              (void *)dst, (void *)old_dst,
              old_dst ? (long long)p_atomic_read(&old_dst->reference.count) : 0,
              (void *)src, src ? (long long)p_atomic_read(&src->reference.count) : 0,
              file, line, function);
   }
   pipe_resource_reference(dst, src);
}
#define pipe_resource_reference(dst, src) \
   station_resource_reference((dst), (src), __FILE__, __LINE__, __func__)
/* STATION_MESA_REF_END */
'''

def sha(data):return hashlib.sha256(data).hexdigest()

def clean_pending_present(source):
    """Apply only the console-probed reference release; no diagnostic logging."""
    name='src/gallium/drivers/zink/zink_context.c'
    path=Path(source)/name
    data=path.read_bytes()
    if sha(data)!=PINNED[name]:raise ValueError('Mesa source differs from pin: '+name)
    text=data.decode('utf-8')
    old='   util_dynarray_fini(&ctx->di.global_bindings);\n\n   ralloc_free(ctx);'
    new=('   util_dynarray_fini(&ctx->di.global_bindings);\n'
         '\n   /* The pending presentation reference outlives framebuffer unbinding. */\n'
         '   if (ctx->needs_present)\n'
         '      zink_resource_reference(&ctx->needs_present, NULL);\n'
         '\n   ralloc_free(ctx);')
    if text.count(old)!=1:raise ValueError('Ambiguous pending presentation cleanup anchor')
    result=text.replace(old,new).encode('utf-8')
    path.write_bytes(result)
    return {name:{'before':PINNED[name],'after':sha(result)}}

def instrument(source, release_pending_present=False):
    source=Path(source);staged={};manifest={}
    for name,wanted in PINNED.items():
        data=(source/name).read_bytes()
        if sha(data)!=wanted:raise ValueError('Mesa source differs from pin: '+name)
        staged[name]=data.decode('utf-8')
    def edit(name,old,new):
        path=next(p for p in PINNED if p.endswith('/'+name))
        if staged[path].count(old)!=1:raise ValueError('Ambiguous diagnostic insertion: '+name)
        staged[path]=staged[path].replace(old,new)
    edit('stw_context.c','stw_destroy_context(struct stw_context *ctx)\n{',
         'stw_destroy_context(struct stw_context *ctx)\n{\n   fprintf(stderr,"STATION_MESA context_destroy ctx=%p st=%p fb=%p read_fb=%p\\n",(void*)ctx,(void*)ctx->st,(void*)ctx->current_framebuffer,(void*)ctx->current_read_framebuffer);')
    edit('stw_context.c','   st_destroy_context(ctx->st);\n   FREE(ctx);',
         '   st_destroy_context(ctx->st);\n   fprintf(stderr,"STATION_MESA context_destroy_done ctx=%p\\n",(void*)ctx);\n   FREE(ctx);')
    edit('stw_framebuffer.c','   /* check the reference count */\n   fb->refcnt--;',
         '   if(fb->refcnt<=2)fprintf(stderr,"STATION_MESA fb_release fb=%p hwnd=%p refs_before=%u owner=%d drawable=%p\\n",(void*)fb,(void*)fb->hWnd,fb->refcnt,fb->owner,(void*)fb->drawable);\n   /* check the reference count */\n   fb->refcnt--;')
    edit('stw_framebuffer.c','   stw_st_destroy_framebuffer_locked(fb->drawable);',
         '   fprintf(stderr,"STATION_MESA fb_destroy fb=%p drawable=%p\\n",(void*)fb,(void*)fb->drawable);\n   stw_st_destroy_framebuffer_locked(fb->drawable);')
    edit('stw_framebuffer.c','      else if (pParams->message == WM_DESTROY) {',
         '      else if (pParams->message == WM_DESTROY) {\n         fprintf(stderr,"STATION_MESA wm_destroy hwnd=%p initialized=%d\\n",(void*)pParams->hwnd,stw_dev->initialized);')
    edit('stw_framebuffer.c','         fb = stw_framebuffer_from_hwnd_hdc_locked( pParams->hwnd, NULL );',
         '         fb = stw_framebuffer_from_hwnd_hdc_locked( pParams->hwnd, NULL );\n         fprintf(stderr,"STATION_MESA wm_destroy_lookup hwnd=%p fb=%p\\n",(void*)pParams->hwnd,(void*)fb);')
    edit('stw_st.c','   struct stw_st_framebuffer *stwfb = stw_st_framebuffer(drawable);\n   int i;',
         '   struct stw_st_framebuffer *stwfb = stw_st_framebuffer(drawable);\n   fprintf(stderr,"STATION_MESA drawable_destroy drawable=%p back=%p\\n",(void*)drawable,(void*)stwfb->back_texture);\n   for(unsigned trace_i=0;trace_i<ST_ATTACHMENT_COUNT;trace_i++){if(stwfb->textures[trace_i])fprintf(stderr,"STATION_MESA attachment index=%u resource=%p refs=%d\\n",trace_i,(void*)stwfb->textures[trace_i],p_atomic_read(&stwfb->textures[trace_i]->reference.count));}\n   int i;')
    edit('zink_resource.c','   /* prevent double-free when unrefing internal surfaces */',
         '   if(res->obj && res->obj->dt)fprintf(stderr,"STATION_MESA resource_destroy resource=%p obj=%p dt=%p\\n",(void*)res,(void*)res->obj,(void*)res->obj->dt);\n   /* prevent double-free when unrefing internal surfaces */')
    edit('zink_resource.c','   } else if (obj->dt) {\n      zink_kopper_displaytarget_destroy(screen, obj->dt);',
         '   } else if (obj->dt) {\n      fprintf(stderr,"STATION_MESA resource_object_destroy obj=%p dt=%p\\n",(void*)obj,(void*)obj->dt);\n      zink_kopper_displaytarget_destroy(screen, obj->dt);')
    edit('zink_kopper.c','   if (!p_atomic_dec_zero(&cdt->refcount))\n      return;',
         '   fprintf(stderr,"STATION_MESA displaytarget_unref dt=%p refs_before=%d surface=%p\\n",(void*)cdt,p_atomic_read(&cdt->refcount),(void*)(uintptr_t)cdt->surface);\n   if (!p_atomic_dec_zero(&cdt->refcount))\n      return;\n   fprintf(stderr,"STATION_MESA displaytarget_destroy dt=%p\\n",(void*)cdt);')
    edit('zink_kopper.c','   if (!cdt->surface)\n      return;',
         '   fprintf(stderr,"STATION_MESA displaytarget_deinit dt=%p surface=%p\\n",(void*)cdt,(void*)(uintptr_t)cdt->surface);\n   if (!cdt->surface)\n      return;')
    edit('zink_context.c','   struct pipe_framebuffer_state fb = {0};\n   pctx->set_framebuffer_state(pctx, &fb);',
         '   fprintf(stderr,"STATION_MESA zink_context_destroy ctx=%p\\n",(void*)ctx);\n   struct pipe_framebuffer_state fb = {0};\n   pctx->set_framebuffer_state(pctx, &fb);')
    edit('u_inlines.h', '   *dst = src;\n}\n\nstatic inline void\npipe_resource_release',
         '   *dst = src;\n}\n' + REFERENCE_TRACE + '\nstatic inline void\npipe_resource_release')
    if release_pending_present:
        # The context owns this reference even when unbinding already emptied
        # fb_state, so set_framebuffer_state(empty) cannot release it. Wait for
        # queues and batch cleanup as usual, then drop exactly this owned ref.
        edit('zink_context.c',
             '   util_dynarray_fini(&ctx->di.global_bindings);\n\n   ralloc_free(ctx);',
             '   util_dynarray_fini(&ctx->di.global_bindings);\n'
             '\n/* STATION_MESA_PENDING_PRESENT_BEGIN */\n'
             '   if (ctx->needs_present) {\n'
             '      fprintf(stderr,"STATION_MESA pending_present_release ctx=%p resource=%p refs=%d\\n",(void*)ctx,(void*)ctx->needs_present,p_atomic_read(&ctx->needs_present->base.b.reference.count));\n'
             '      zink_resource_reference(&ctx->needs_present, NULL);\n'
             '   }\n'
             '/* STATION_MESA_PENDING_PRESENT_END */\n'
             '\n   ralloc_free(ctx);')
    for name,text in staged.items():
        if '#include <stdio.h>' not in text:
            at=text.index('#include ');text=text[:at]+'#include <stdio.h>\n'+text[at:]
        data=text.encode('utf-8');manifest[name]={'before':PINNED[name],'after':sha(data)}
        (source/name).write_bytes(data)
    return manifest

if __name__=='__main__':
    import sys
    print(json.dumps(instrument(Path(sys.argv[1])),indent=2))
