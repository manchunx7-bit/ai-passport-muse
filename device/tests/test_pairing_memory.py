# SPDX-License-Identifier: Apache-2.0
"""Run production pairing/RX code with sanitizers and synthetic credentials.

Only platform boundaries are mocked. No device logs, firmware dumps, network
settings or real account material are read by these tests.
"""
import base64
import json
import os
from pathlib import Path
import random
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SDK = ROOT / 'components/passport_muse/sdk'


def cstring(value):
    if isinstance(value, str):
        value = value.encode()
    return '"' + ''.join(f'\\x{b:02x}' for b in value) + '"'


BLE_PLATFORM = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdatomic.h>
#include "cJSON.h"
#include "ble_server.h"
typedef int BaseType_t;
typedef unsigned UBaseType_t;
typedef void *TaskHandle_t;
typedef void (*TaskFunction_t)(void *);
typedef void *SemaphoreHandle_t;
typedef int stack_monitor_t;
#define STACK_MONITOR_INIT 0
#define pdPASS 1
#define pdFAIL 0
#define portMAX_DELAY 0
#define pdMS_TO_TICKS(n) (n)
#define BLE_HS_CONN_HANDLE_NONE UINT16_MAX
#define BLE_ERR_REM_USER_CONN_TERM 19
#define BLE_GATT_ACCESS_OP_WRITE_CHR 1
#define BLE_GATT_ACCESS_OP_READ_CHR 2
#define BLE_ATT_ERR_UNLIKELY 14
#define BLE_ATT_ERR_INSUFFICIENT_RES 17
#define MALLOC_CAP_8BIT 4
#define ESP_LOGI(...) ((void)0)
#define ESP_LOGW(...) ((void)0)
#define ESP_LOGE(...) ((void)0)
typedef struct { const char *version; } esp_app_desc_t;
static const esp_app_desc_t *esp_app_get_description(void) {
    static esp_app_desc_t d={"test"}; return &d;
}
static unsigned esp_get_free_heap_size(void) { return 12000; }
static unsigned heap_caps_get_largest_free_block(unsigned caps) { (void)caps; return 4096; }
static void xSemaphoreTake(SemaphoreHandle_t lock,int wait) { (void)lock;(void)wait; }
static void xSemaphoreGive(SemaphoreHandle_t lock) { (void)lock; }
static void vTaskDelay(int ticks) { (void)ticks; }
static void vTaskDelete(void *task) { assert(!task); }
static void stack_monitor_record(void *p) { (void)p; }
static int ble_gap_terminate(uint16_t handle,int reason) { (void)handle;(void)reason;return 0; }

typedef struct { void *pointer;size_t size;size_t sensitive; } block_t;
static block_t blocks[2048];
static size_t live_bytes,peak_bytes,live_blocks,max_request;
static unsigned allocation_calls,fail_at;
static bool allocation_failed,task_failure,confirmed=true,session_live=true;
static bool marked,cancel_on_flat_free,shutdown_on_flat_free,direct_decrypted;
static unsigned calls,created,rejected,disconnected;
static void *flat_buffer;
static const char *plain_json;
static void on_flat_free(void);
static block_t *block(void *p) {
    for(size_t i=0;i<2048;i++) if(blocks[i].pointer==p) return &blocks[i];
    return NULL;
}
static void *tracked_malloc(size_t n) {
    allocation_calls++;
    if(n>max_request) max_request=n;
    if(n>8192 || (fail_at && allocation_calls==fail_at)) { allocation_failed=true;return NULL; }
    void *p=malloc(n?n:1);assert(p);
    for(size_t i=0;i<2048;i++) if(!blocks[i].pointer) {
        blocks[i]=(block_t){p,n,false};live_bytes+=n;live_blocks++;
        if(live_bytes>peak_bytes) peak_bytes=live_bytes;
        return p;
    }
    abort();
}
static void tracked_free(void *p) {
    if(!p) return;
    block_t *b=block(p);assert(b);
    if(b->sensitive) for(size_t i=0;i<b->sensitive;i++) assert(((unsigned char*)p)[i]==0);
    if(p==flat_buffer) { flat_buffer=NULL;on_flat_free(); }
    live_bytes-=b->size;live_blocks--;b->pointer=NULL;free(p);
}
static void *tracked_calloc(size_t n,size_t s) {
    void *p=tracked_malloc(n*s);if(p) memset(p,0,n*s);return p;
}
static void *tracked_realloc(void *p,size_t n) {
    void *next=tracked_malloc(n);if(!next) return NULL;
    if(p) { block_t *old=block(p);assert(old);memcpy(next,p,n<old->size?n:old->size);tracked_free(p); }
    return next;
}
static void *tracked_memcpy(void *dst,const void *src,size_t n) {
    block_t *from=block((void*)src),*to=block(dst);
    if(from && from->sensitive && to) to->sensitive=n;
    return memcpy(dst,src,n);
}
static void mbedtls_platform_zeroize(void *p,size_t n) {
    volatile unsigned char *v=p;while(n--) *v++=0;
}
static void mark_values(cJSON *root) {
    for(cJSON *p=root;p;p=p->next) {
        if(p->valuestring) { block_t *b=block(p->valuestring);assert(b);b->sensitive=strlen(p->valuestring)+1; }
        if(p->child) mark_values(p->child);
    }
}
static cJSON *spy_parse(const char *data,size_t len) {
    cJSON *root=cJSON_ParseWithLength(data,len);
    cJSON *action=cJSON_GetObjectItem(root,"action");
    block_t *input=block((void*)data);
    if((direct_decrypted || (input && input->sensitive))
       && cJSON_IsString(action) && !strcmp(action->valuestring,"provision_v2")) mark_values(root);
    return root;
}
struct os_mbuf { const uint8_t *data;uint16_t len; };
struct ble_gatt_access_ctxt { int op;struct os_mbuf *om; };
#define OS_MBUF_PKTLEN(m) ((m)->len)
static int ble_hs_mbuf_to_flat(struct os_mbuf *m,void *out,size_t cap,uint16_t *len) {
    assert(cap>=m->len);memcpy(out,m->data,m->len);*len=m->len;flat_buffer=out;return 0;
}
static int os_mbuf_append(struct os_mbuf *m,const void *p,size_t n) { (void)m;(void)p;(void)n;return 0; }
static bool config_setup_complete(void) { return false; }
static bool link_pairing_plaintext_setup_blocked(void) { return true; }
static bool link_pairing_session_confirmed(void) { return confirmed; }
static bool link_pairing_session_is_current(uint32_t g) { return session_live && g==7; }
static bool link_pairing_provisioning_session_valid(uint32_t g) { return session_live && g==7; }
static uint32_t link_pairing_mark_provisioning_active(void) { marked=true;return session_live?7:0; }
static uint32_t link_pairing_handle_client_finished(void) { return 7; }
static void link_pairing_reset(void) { session_live=false; }
static const char *link_pairing_handle_client_hello(cJSON *r,char **reply) {
    (void)r;*reply=NULL;return "error_pairing_invalid_hello";
}
static const char *link_pairing_decrypt_command(cJSON *root,char **plain) {
    assert(cJSON_IsString(cJSON_GetObjectItem(root,"ciphertext")));
    if(!session_live) return "error_pairing_decrypt";
    size_t n=strlen(plain_json)+1;*plain=tracked_malloc(n);
    if(!*plain) return "error_pairing_decrypt";
    memcpy(*plain,plain_json,n);block(*plain)->sensitive=n;return NULL;
}
void ble_server_send_status(const char *s) { assert(s);rejected++; }
bool ble_server_send_pairing_status(const char *s,uint32_t g) { assert(s);(void)g;rejected++;return true; }
void ble_server_disconnect_pairing_session(uint32_t g) { (void)g;disconnected++; }
void ble_server_send_chunked(const char *s) { assert(s); }
static BaseType_t xTaskCreate(TaskFunction_t fn,const char *name,uint32_t stack,
                              void *arg,UBaseType_t priority,TaskHandle_t *handle);
#define malloc tracked_malloc
#define calloc tracked_calloc
#define realloc tracked_realloc
#define free tracked_free
#define memcpy tracked_memcpy
#define cJSON_ParseWithLength spy_parse
'''


BLE_CASES = r'''
#undef malloc
#undef calloc
#undef realloc
#undef free
#undef memcpy
#undef cJSON_ParseWithLength
static struct { TaskFunction_t fn;void *arg; } tasks[8];
static unsigned task_count;
static void on_flat_free(void) {
    if(marked && cancel_on_flat_free) session_live=false;
    if(marked && shutdown_on_flat_free) s_shutting_down=true;
}
static BaseType_t xTaskCreate(TaskFunction_t fn,const char *name,uint32_t stack,
                              void *arg,UBaseType_t priority,TaskHandle_t *handle) {
    (void)priority;(void)handle;
    if(!strcmp(name,"prov")) {
        provision_args_t *a=arg;
        assert(fn==provision_task && stack==4096 && !flat_buffer && !s_rx_buf);
        char *strings[]={a->ssid,a->password,a->access_token,a->refresh_token,a->username,
                         a->ota_url,a->api_url,a->api_url_v2,a->noise_host};
        size_t owned=sizeof(*a),count=1;
        for(size_t i=0;i<sizeof(strings)/sizeof(strings[0]);i++) if(strings[i]) {
            owned+=strlen(strings[i])+1;count++;
        }
        // At the RTOS boundary only copied credentials remain. This catches
        // task creation before packet/plaintext/JSON release, not just order.
        assert(live_bytes==owned && live_blocks==count);
        if(task_failure) return pdFAIL;
        created++;
    }
    assert(task_count<8);tasks[task_count].fn=fn;tasks[task_count++].arg=arg;return pdPASS;
}
static void on_provision(const char *ssid,const char *password,const char *access,
                         const char *refresh,const char *username,const char *ota,bool force,
                         const char *api,const char *v2,const char *host,uint32_t generation) {
    assert(!strcmp(ssid,"test-network") && !strcmp(password,"test-password"));
    assert(strlen(access)>1000 && strlen(refresh)>200 && !strcmp(username,"test-user"));
    assert(!strcmp(ota,"https://example.invalid/image") && !force);
    assert(!strcmp(api,"https://api.example.invalid") && !strcmp(v2,api));
    assert(!strcmp(host,"example.invalid") && generation==7);calls++;
}
static void drain(void) {
    for(unsigned i=0;i<task_count;i++) tasks[i].fn(tasks[i].arg);
    task_count=0;assert(atomic_load(&s_dispatch_tasks)==0);
}
static int packet(const uint8_t *p,size_t n) {
    assert(n<=UINT16_MAX);struct os_mbuf m={p,(uint16_t)n};
    struct ble_gatt_access_ctxt c={BLE_GATT_ACCESS_OP_WRITE_CHR,&m};
    return rx_access_cb(1,1,&c,NULL);
}
static void feed(const char *json) {
    size_t n=strlen(json),total=(n+249)/250;
    for(size_t i=0;i<total;i++) {
        uint8_t p[253]={CHUNK_MAGIC,(uint8_t)i,(uint8_t)total};
        size_t length=n-i*250;if(length>250) length=250;
        memcpy(p+3,json+i*250,length);(void)packet(p,length+3);
    }
}
static void reset(void) {
    drain();rx_reset_locked();assert(live_bytes==0 && live_blocks==0);
    memset(blocks,0,sizeof(blocks));s_rx_mutex=(void *)1;allocation_calls=0;fail_at=0;
    allocation_failed=false;task_failure=false;confirmed=true;session_live=true;
    marked=false;cancel_on_flat_free=false;shutdown_on_flat_free=false;
    calls=created=rejected=disconnected=0;peak_bytes=max_request=0;
    s_shutting_down=false;s_plaintext_status_blocked=false;s_cb.on_provision=on_provision;
}
static void clean(void) { drain();rx_reset_locked();assert(live_bytes==0 && live_blocks==0); }
static void success(void) {
    feed(envelope);assert(created==1 && calls==0);assert(max_request<8192);
    drain();assert(calls==1 && !rejected);clean();
}
static void allocation_faults(void) {
    success();unsigned attempts=allocation_calls;
    for(unsigned i=1;i<=attempts;i++) {
        reset();fail_at=i;feed(envelope);drain();assert(allocation_failed);
        fail_at=0;feed(envelope);drain();assert(calls>=1);clean();
    }
}
static void rx_boundaries(void) {
    uint8_t payload[8193];memset(payload,'x',sizeof(payload));
    for(size_t length=8192;length<=8193;length++) {
        uint8_t *complete=NULL;size_t complete_len=0;size_t total=(length+249)/250;
        for(size_t i=0;i<total;i++) {
            uint8_t p[253]={CHUNK_MAGIC,(uint8_t)i,(uint8_t)total};
            size_t n=length-i*250;if(n>250) n=250;memcpy(p+3,payload+i*250,n);
            handle_rx_write_locked(p,n+3,&complete,&complete_len);
        }
        if(length==8192) { assert(complete && complete_len==length && !memcmp(complete,payload,length));tracked_free(complete); }
        else assert(!complete);
        rx_reset_locked();assert(live_blocks==0);
    }
    // The estimate must grow safely for nonuniform fragment lengths.
    uint8_t *out=NULL;size_t n=0;
    const uint8_t first[]={CHUNK_MAGIC,0,3,'a'};
    const uint8_t wrong[]={CHUNK_MAGIC,2,3,'c'};
    handle_rx_write_locked(first,sizeof(first),&out,&n);
    handle_rx_write_locked(wrong,sizeof(wrong),&out,&n);assert(!out && !s_rx_buf);
    handle_rx_write_locked(first,sizeof(first),&out,&n);
    uint8_t next[253]={CHUNK_MAGIC,1,3};memset(next+3,'b',250);
    handle_rx_write_locked(next,sizeof(next),&out,&n);next[1]=2;
    handle_rx_write_locked(next,sizeof(next),&out,&n);
    assert(n==501 && out[0]=='a' && out[500]=='b');tracked_free(out);clean();
}
int main(int argc,char **argv) {
    assert(argc==2);cJSON_Hooks hooks={tracked_malloc,tracked_free};cJSON_InitHooks(&hooks);
    plain_json=provision_json;reset();
    switch(atoi(argv[1])) {
    case 0:success();break;
    case 1:allocation_faults();break;
    case 2:rx_boundaries();break;
    case 3:cancel_on_flat_free=true;feed(envelope);assert(!created && disconnected);clean();break;
    case 4:shutdown_on_flat_free=true;feed(envelope);assert(!created && disconnected);clean();break;
    case 5:task_failure=true;feed(envelope);assert(!created && disconnected);clean();break;
    case 6:assert(packet((const uint8_t*)provision_json,strlen(provision_json))==0);assert(!created && rejected);clean();break;
    case 7:confirmed=false;feed(envelope);assert(!created && rejected);clean();break;
    case 8:feed(envelope);assert(created==1);session_live=false;drain();assert(!calls);clean();break;
    case 9:{
        direct_decrypted=true;
        rx_dispatch_t d={0};
        dispatch_command_ex((const uint8_t*)provision_json,strlen(provision_json),true,&d);
        provision_args_t *first=d.provision;assert(first);
        dispatch_command_ex((const uint8_t*)provision_json,strlen(provision_json),true,&d);
        assert(d.provision==first && disconnected);flush_provision(&d);clean();break;
    }
    default:return 2;
    }
    return 0;
}
'''


class PairingMemory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cjson = Path(os.environ.get('IDF_PATH', '/opt/esp-idf')) / 'components/json/cJSON'
        source = (SDK / 'ble_server.c').read_text()
        # Compile every production RX/dispatch/ownership function together;
        # exclude hardware UUID registration and the unrelated TX/GAP backend.
        source = source[source.index('#define MAX_NOTIFY_CHUNK'):source.index('// ---- Service definition')]
        source = source.replace('static void start_advertising(void);', '')
        plain = json.dumps(dict(action='provision_v2', ssid='test-network', password='test-password',
                                access_token='synthetic-access-'+'a'*1400,
                                refresh_token='synthetic-refresh-'+'b'*256,
                                username='test-user', token_type='device',
                                api_url='https://api.example.invalid', api_url_v2='https://api.example.invalid',
                                noise_host='example.invalid', ota_url='https://example.invalid/image'), separators=(',', ':'))
        prefix = '{"action":"pairing_encrypted","ciphertext":"'
        envelope = prefix + 'x'*(2783-len(prefix)-2) + '"}'
        assert len(envelope) == 2783
        fixtures = f'\nstatic const char *provision_json={cstring(plain)};\nstatic const char *envelope={cstring(envelope)};\n'
        code = BLE_PLATFORM + source + fixtures + BLE_CASES
        cls.binary = Path(cls.tmp.name) / 'pairing'
        cfile = cls.binary.with_suffix('.c')
        cfile.write_text(code)
        subprocess.run([os.environ.get('CC', 'cc'), '-std=gnu11', '-Wall', '-Wextra', '-Werror',
                        '-Wno-unused-function', '-Wno-unused-variable', '-Wno-unused-parameter',
                        '-Wno-deprecated-declarations',
                        '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                        '-I', str(cjson), '-I', str(SDK), str(cfile), str(cjson/'cJSON.c'),
                        '-o', str(cls.binary)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_case(self, case):
        subprocess.run([str(self.binary), str(case)], check=True)

    def test_task_created_only_after_all_message_allocations_are_freed(self): self.run_case(0)
    def test_every_allocation_failure_releases_secrets_and_allows_retry(self): self.run_case(1)
    def test_rx_limit_growth_and_out_of_order_recovery(self): self.run_case(2)
    def test_disconnect_between_staging_and_task_creation(self): self.run_case(3)
    def test_shutdown_between_staging_and_task_creation(self): self.run_case(4)
    def test_rtos_allocation_failure_cleans_pending_credentials(self): self.run_case(5)
    def test_plaintext_provision_stays_blocked(self): self.run_case(6)
    def test_encrypted_provision_still_requires_physical_confirmation(self): self.run_case(7)
    def test_replaced_session_does_not_run_queued_provision_callback(self): self.run_case(8)
    def test_duplicate_staged_provision_does_not_replace_its_owner(self): self.run_case(9)


class Base64Memory(unittest.TestCase):
    def test_decoder_vectors_capacities_invalid_bytes_and_no_allocation(self):
        source = (SDK/'link_pairing.c').read_text()
        source = source[source.index('static int base64url_digit'):source.index('static bool json_string')]
        rng = random.Random(64)
        vectors = []
        for length in list(range(1, 130)) + list(range(1985, 1994)) + [3070, 3071, 3072]:
            value = rng.randbytes(length)
            encoded = base64.urlsafe_b64encode(value).rstrip(b'=')
            vectors.append('{'+cstring(encoded)+', (const uint8_t*)'+cstring(value)+f', {length}'+'}')
        code = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#define malloc(...) forbidden_temporary_allocation
#define calloc(...) forbidden_temporary_allocation
#define realloc(...) forbidden_temporary_allocation
''' + source + r'''
#undef malloc
#undef calloc
#undef realloc
struct vector {const char *encoded;const uint8_t *decoded;size_t n;};
static const struct vector vectors[]={
''' + ',\n'.join(vectors) + r'''
};
int main(void) {
    uint8_t out[4112];char input[5000];size_t written;
    for(size_t i=0;i<sizeof(vectors)/sizeof(vectors[0]);i++) {
        const struct vector *v=&vectors[i];strcpy(input,v->encoded);
        memset(out,0xa5,sizeof(out));written=123;
        assert(base64url_decode(input,out,v->n,&written) && written==v->n);
        assert(!memcmp(out,v->decoded,v->n) && !strcmp(input,v->encoded));
        for(size_t j=v->n;j<sizeof(out);j++) assert(out[j]==0xa5);
        memset(out,0xa5,sizeof(out));written=123;
        assert(!base64url_decode(input,out,v->n-1,&written) && written==123);
        for(size_t j=0;j<sizeof(out);j++) assert(out[j]==0xa5);
    }
    const char *alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";
    for(unsigned c=1;c<256;c++) for(unsigned position=0;position<12;position+=3) {
        memset(input,'A',12);input[12]=0;input[position]=(char)c;
        memset(out,0xa5,sizeof(out));written=123;
        bool valid=strchr(alphabet,(int)c)!=NULL;
        assert(base64url_decode(input,out,sizeof(out),&written)==valid);
        if(!valid) { assert(written==123);for(size_t j=0;j<sizeof(out);j++) assert(out[j]==0xa5); }
    }
    const char *bad[]={"","A","AAAA=","AA==","AA+A","AA/A","AA A","AA\nA"};
    for(size_t i=0;i<sizeof(bad)/sizeof(bad[0]);i++) assert(!base64url_decode(bad[i],out,sizeof(out),&written));
    memset(input,'A',4097);input[4097]=0;assert(!base64url_decode(input,out,sizeof(out),&written));
    assert(!base64url_decode(NULL,out,sizeof(out),&written));
    assert(!base64url_decode("AAAA",NULL,sizeof(out),&written));
    assert(!base64url_decode("AAAA",out,sizeof(out),NULL));
    return 0;
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            cfile = Path(tmp)/'decode.c'
            binary = Path(tmp)/'decode'
            cfile.write_text(code)
            subprocess.run([os.environ.get('CC', 'cc'), '-std=c11', '-Wall', '-Wextra', '-Werror',
                            '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                            str(cfile), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)


if __name__ == '__main__':
    unittest.main()
