// Exercise the production Noise crypto/framer with the C3's shared RX/plaintext
// storage. Build against mbedcrypto; no fake crypto or network credentials.
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <vector>
#include <psa/crypto.h>
#include <xplat/noise/core/PsaCryptoBackend.h>
#include <xplat/noise/core/Transport.h>
#include <xplat/noise/core/TransportFrameCodec.h>

namespace n = musegadgets::noise::core;

#ifdef TRACK_MUSE_AES_ALLOC
static bool track_alloc;
static size_t largest_aes_alloc;
extern "C" void *__real_calloc(size_t, size_t);
extern "C" void *__wrap_calloc(size_t count, size_t size) {
    if (track_alloc) largest_aes_alloc = std::max(largest_aes_alloc, count * size);
    return __real_calloc(count, size);
}
#endif

static void track_aes(bool start) {
#ifdef TRACK_MUSE_AES_ALLOC
    track_alloc = start;
    if (!start) assert(largest_aes_alloc <= 2048);
#else
    (void)start;
#endif
}

static void authenticated_inplace(n::PsaCryptoBackend &crypto) {
    std::array<uint8_t, 32> key{};
    std::array<uint8_t, 12> nonce{};
    std::array<uint8_t, 3> aad{{1, 7, 9}};
    std::vector<uint8_t> plain(16 * 1024);
    for (size_t i = 0; i < plain.size(); ++i) plain[i] = (i * 31) & 255;
    std::vector<uint8_t> guarded(plain.size() + 16 + 2, 0xa5);
    auto *rx = guarded.data() + 1;
    track_aes(true);
    assert(crypto.Aes256GcmSeal(n::ConstByteSpan(key), n::ConstByteSpan(nonce),
        n::ConstByteSpan(aad), n::ConstByteSpan(plain.data(), plain.size()),
        n::ByteSpan(rx, plain.size() + 16)).ok());
    track_aes(false);
    const std::vector<uint8_t> encrypted(rx, rx + plain.size() + 16);
    // Byte-for-byte compatibility with the independent PSA API path.
    assert(psa_crypto_init() == PSA_SUCCESS);
    psa_key_attributes_t attributes = PSA_KEY_ATTRIBUTES_INIT;
    psa_set_key_usage_flags(&attributes, PSA_KEY_USAGE_ENCRYPT);
    psa_set_key_algorithm(&attributes, PSA_ALG_GCM);
    psa_set_key_type(&attributes, PSA_KEY_TYPE_AES);
    psa_set_key_bits(&attributes, 256);
    mbedtls_svc_key_id_t imported{};
    assert(psa_import_key(&attributes, key.data(), key.size(), &imported) == PSA_SUCCESS);
    std::vector<uint8_t> reference(encrypted.size());
    size_t written = 0;
    assert(psa_aead_encrypt(imported, PSA_ALG_GCM, nonce.data(), nonce.size(),
        aad.data(), aad.size(), plain.data(), plain.size(), reference.data(),
        reference.size(), &written) == PSA_SUCCESS);
    assert(psa_destroy_key(imported) == PSA_SUCCESS);
    assert(written == reference.size() && reference == encrypted);
    track_aes(true);
    assert(crypto.Aes256GcmOpen(n::ConstByteSpan(key), n::ConstByteSpan(nonce),
        n::ConstByteSpan(aad), n::ConstByteSpan(rx, plain.size() + 16),
        n::ByteSpan(rx, plain.size())).ok());
    track_aes(false);
    assert(std::equal(plain.begin(), plain.end(), rx));
    assert(guarded.front() == 0xa5 && guarded.back() == 0xa5);

    // A corrupted tag must still fail authentication and erase plaintext.
    std::copy(encrypted.begin(), encrypted.end(), rx);
    rx[encrypted.size() - 1] ^= 1;
    assert(!crypto.Aes256GcmOpen(n::ConstByteSpan(key), n::ConstByteSpan(nonce),
        n::ConstByteSpan(aad), n::ConstByteSpan(rx, encrypted.size()),
        n::ByteSpan(rx, plain.size())).ok());
    assert(std::all_of(rx, rx + plain.size(), [](uint8_t v) { return v == 0; }));
    assert(guarded.front() == 0xa5 && guarded.back() == 0xa5);
}

static void empty_body(n::PsaCryptoBackend &crypto) {
    std::array<uint8_t, 32> key{};
    std::array<uint8_t, 12> nonce{};
    std::array<uint8_t, 16> tag{};
    assert(crypto.Aes256GcmSeal(n::ConstByteSpan(key), n::ConstByteSpan(nonce),
        n::ConstByteSpan(), n::ConstByteSpan(), n::ByteSpan(tag)).ok());
    assert(crypto.Aes256GcmOpen(n::ConstByteSpan(key), n::ConstByteSpan(nonce),
        n::ConstByteSpan(), n::ConstByteSpan(tag), n::ByteSpan()).ok());
    tag[0] ^= 1;
    assert(!crypto.Aes256GcmOpen(n::ConstByteSpan(key), n::ConstByteSpan(nonce),
        n::ConstByteSpan(), n::ConstByteSpan(tag), n::ByteSpan()).ok());
}

static void fragmented_inplace(n::PsaCryptoBackend &crypto) {
    std::array<uint8_t, 32> key_a{}, key_b{};
    key_b.fill(0x32);
    n::Transport sender(crypto, n::ConstByteSpan(key_a), n::ConstByteSpan(key_b));
    n::Transport receiver(crypto, n::ConstByteSpan(key_b), n::ConstByteSpan(key_a));
    n::OrderedTransportFramer framer;
    std::vector<uint8_t> message(16 * 1024);
    for (size_t i = 0; i < message.size(); ++i) message[i] = (i * 13) & 255;
    std::vector<uint8_t> frame(17 * 1024), guarded_rx(17 * 1024 + 2, 0xa5);
    std::vector<uint8_t> guarded_service(17 * 1024 + 2, 0xa5);
    uint8_t *rx = guarded_rx.data() + 1, *service = guarded_service.data() + 1;
    for (size_t chunk = 0; chunk < 4; ++chunk) {
        // The next receive overwrites all of RX. Earlier fragments must live
        // independently in service storage, even when decrypting in place.
        std::fill(rx, rx + 17 * 1024, 0xee);
        n::TransportFrameView view;
        view.chunk_id = 7; view.chunk_index = chunk; view.total_chunks = 4;
        view.payload = n::ConstByteSpan(message.data() + chunk * 4096, 4096);
        auto encoded = n::EncodeTransportFrame(view, n::ByteSpan(frame.data(), frame.size()));
        assert(encoded.ok());
        auto encrypted = sender.Seal(n::ConstByteSpan(frame.data(), encoded.size()),
                                    n::ByteSpan(rx, 17 * 1024));
        assert(encrypted.ok());
        auto opened = receiver.Open(n::ConstByteSpan(rx, encrypted.size()),
                                    n::ByteSpan(rx, 17 * 1024));
        assert(opened.ok());
        auto assembled = framer.DecodeAndAppendInboundFrame(
            n::ConstByteSpan(rx, opened.size()), n::ByteSpan(service, 17 * 1024));
        assert(assembled.status.ok());
        assert(assembled.frame_status == (chunk == 3 ? n::InboundFrameStatus::Complete
                                                     : n::InboundFrameStatus::NeedMore));
        assert(assembled.size == (chunk + 1) * 4096);
        assert(std::equal(message.begin(), message.begin() + assembled.size, service));
    }
    assert(guarded_rx.front() == 0xa5 && guarded_rx.back() == 0xa5);
    assert(guarded_service.front() == 0xa5 && guarded_service.back() == 0xa5);
}

int main() {
    n::PsaCryptoBackend crypto;
    authenticated_inplace(crypto);
    empty_body(crypto);
    fragmented_inplace(crypto);
    std::puts("PASS: 16 KiB in-place decryption, PSA byte compatibility, tag rejection, empty body, four-frame reassembly, buffer guards");
#ifdef TRACK_MUSE_AES_ALLOC
    std::printf("Largest C3 GCM calloc for a 16 KiB payload: %zu bytes\n", largest_aes_alloc);
#endif
}
