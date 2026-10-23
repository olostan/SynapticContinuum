"""Vulkan compute kernels using wgpu targeting AMD Radeon Vega 7 (RADV RENOIR)."""

import time
import numpy as np
import wgpu


class VulkanEngine:
    def __init__(self):
        t0 = time.perf_counter()
        self.adapter = wgpu.gpu.request_adapter_sync()
        self.device = self.adapter.request_device_sync()
        self.init_time_ms = (time.perf_counter() - t0) * 1000.0

        self.info = self.adapter.info
        self.device_name = self.info.get("device", "Unknown")
        self.backend_type = self.info.get("backend_type", "Unknown")

        # Compile shader pipelines
        self._init_gemm_pipeline()
        self._init_trace_decay_pipeline()
        self._init_recurrent_pipeline()
        self._init_sparse_scatter_pipeline()

    def _init_gemm_pipeline(self):
        # Matrix multiplication C[M, P] = A[M, K] * B[K, P]
        wgsl = """
        struct Params {
            M: u32,
            K: u32,
            P: u32,
            _pad: u32,
        };

        @group(0) @binding(0) var<uniform> params: Params;
        @group(0) @binding(1) var<storage, read> A: array<f32>;
        @group(0) @binding(2) var<storage, read> B: array<f32>;
        @group(0) @binding(3) var<storage, read_write> C: array<f32>;

        @compute @workgroup_size(16, 16)
        fn main(@builtin(global_invocation_id) gid: vec3<u32>) {
            let row = gid.y;
            let col = gid.x;

            if (row < params.M && col < params.P) {
                var sum: f32 = 0.0;
                for (var i: u32 = 0u; i < params.K; i = i + 1u) {
                    sum = sum + A[row * params.K + i] * B[i * params.P + col];
                }
                C[row * params.P + col] = sum;
            }
        }
        """
        mod = self.device.create_shader_module(code=wgsl)
        self.gemm_pipeline = self.device.create_compute_pipeline(
            layout="auto",
            compute={"module": mod, "entry_point": "main"}
        )

    def _init_trace_decay_pipeline(self):
        # Trace decay: Z[N, K] = alpha[K] * Z[N, K] + (1 - alpha[K]) * H[N]
        wgsl = """
        struct Params {
            N: u32,
            K: u32,
            _pad1: u32,
            _pad2: u32,
        };

        @group(0) @binding(0) var<uniform> params: Params;
        @group(0) @binding(1) var<storage, read> H: array<f32>;
        @group(0) @binding(2) var<storage, read> alpha: array<f32>;
        @group(0) @binding(3) var<storage, read_write> Z: array<f32>;

        @compute @workgroup_size(64)
        fn main(@builtin(global_invocation_id) gid: vec3<u32>) {
            let idx = gid.x;
            let total = params.N * params.K;
            if (idx < total) {
                let neuron = idx / params.K;
                let k = idx % params.K;
                let a = alpha[k];
                let h_val = H[neuron];
                Z[idx] = a * Z[idx] + (1.0 - a) * h_val;
            }
        }
        """
        mod = self.device.create_shader_module(code=wgsl)
        self.trace_pipeline = self.device.create_compute_pipeline(
            layout="auto",
            compute={"module": mod, "entry_point": "main"}
        )

    def _init_recurrent_pipeline(self):
        # Recurrent state step: h_next = tanh(W * h + b + x) for 1 vector
        wgsl = """
        struct Params {
            N: u32,
            _pad1: u32,
            _pad2: u32,
            _pad3: u32,
        };

        @group(0) @binding(0) var<uniform> params: Params;
        @group(0) @binding(1) var<storage, read> W: array<f32>;
        @group(0) @binding(2) var<storage, read> h: array<f32>;
        @group(0) @binding(3) var<storage, read> b: array<f32>;
        @group(0) @binding(4) var<storage, read> x: array<f32>;
        @group(0) @binding(5) var<storage, read_write> h_next: array<f32>;

        @compute @workgroup_size(64)
        fn main(@builtin(global_invocation_id) gid: vec3<u32>) {
            let i = gid.x;
            if (i < params.N) {
                var dot: f32 = 0.0;
                let row_offset = i * params.N;
                for (var j: u32 = 0u; j < params.N; j = j + 1u) {
                    dot = dot + W[row_offset + j] * h[j];
                }
                let val = dot + b[i] + x[i];
                h_next[i] = tanh(val);
            }
        }
        """
        mod = self.device.create_shader_module(code=wgsl)
        self.recurrent_pipeline = self.device.create_compute_pipeline(
            layout="auto",
            compute={"module": mod, "entry_point": "main"}
        )

    def _init_sparse_scatter_pipeline(self):
        # Sparse scatter / gather propagation:
        # Given active indices and sparse edges: h_out[dst] += weight * h[src]
        wgsl = """
        struct Params {
            num_edges: u32,
            _pad1: u32,
            _pad2: u32,
            _pad3: u32,
        };

        @group(0) @binding(0) var<uniform> params: Params;
        @group(0) @binding(1) var<storage, read> src_nodes: array<u32>;
        @group(0) @binding(2) var<storage, read> dst_nodes: array<u32>;
        @group(0) @binding(3) var<storage, read> edge_weights: array<f32>;
        @group(0) @binding(4) var<storage, read> h_in: array<f32>;
        @group(0) @binding(5) var<storage, read_write> h_out: array<atomic<i32>>;

        // Fixed-point scaling for atomic addition (scale factor = 10000)
        @compute @workgroup_size(64)
        fn main(@builtin(global_invocation_id) gid: vec3<u32>) {
            let e = gid.x;
            if (e < params.num_edges) {
                let src = src_nodes[e];
                let dst = dst_nodes[e];
                let w = edge_weights[e];
                let val = h_in[src] * w;
                let fixed_val = i32(val * 10000.0);
                atomicAdd(&h_out[dst], fixed_val);
            }
        }
        """
        mod = self.device.create_shader_module(code=wgsl)
        self.sparse_scatter_pipeline = self.device.create_compute_pipeline(
            layout="auto",
            compute={"module": mod, "entry_point": "main"}
        )

    def run_gemm(self, A: np.ndarray, B: np.ndarray) -> np.ndarray:
        M, K = A.shape
        K2, P = B.shape
        assert K == K2, f"Shape mismatch: {A.shape} vs {B.shape}"

        params = np.array([M, K, P, 0], dtype=np.uint32)
        p_buf = self.device.create_buffer_with_data(data=params, usage=wgpu.BufferUsage.UNIFORM)
        a_buf = self.device.create_buffer_with_data(data=A.astype(np.float32), usage=wgpu.BufferUsage.STORAGE)
        b_buf = self.device.create_buffer_with_data(data=B.astype(np.float32), usage=wgpu.BufferUsage.STORAGE)
        c_size = M * P * 4
        c_buf = self.device.create_buffer(size=c_size, usage=wgpu.BufferUsage.STORAGE | wgpu.BufferUsage.COPY_SRC)

        bind_group = self.device.create_bind_group(
            layout=self.gemm_pipeline.get_bind_group_layout(0),
            entries=[
                {"binding": 0, "resource": {"buffer": p_buf, "offset": 0, "size": p_buf.size}},
                {"binding": 1, "resource": {"buffer": a_buf, "offset": 0, "size": a_buf.size}},
                {"binding": 2, "resource": {"buffer": b_buf, "offset": 0, "size": b_buf.size}},
                {"binding": 3, "resource": {"buffer": c_buf, "offset": 0, "size": c_buf.size}},
            ]
        )

        enc = self.device.create_command_encoder()
        cp = enc.begin_compute_pass()
        cp.set_pipeline(self.gemm_pipeline)
        cp.set_bind_group(0, bind_group)
        cp.dispatch_workgroups((P + 15) // 16, (M + 15) // 16, 1)
        cp.end()

        self.device.queue.submit([enc.finish()])
        out = np.frombuffer(self.device.queue.read_buffer(c_buf), dtype=np.float32).reshape(M, P)
        return out

    def run_trace_decay(self, Z: np.ndarray, H: np.ndarray, alpha: np.ndarray) -> np.ndarray:
        N, K = Z.shape
        params = np.array([N, K, 0, 0], dtype=np.uint32)
        p_buf = self.device.create_buffer_with_data(data=params, usage=wgpu.BufferUsage.UNIFORM)
        h_buf = self.device.create_buffer_with_data(data=H.astype(np.float32), usage=wgpu.BufferUsage.STORAGE)
        a_buf = self.device.create_buffer_with_data(data=alpha.astype(np.float32), usage=wgpu.BufferUsage.STORAGE)
        z_buf = self.device.create_buffer_with_data(data=Z.astype(np.float32), usage=wgpu.BufferUsage.STORAGE | wgpu.BufferUsage.COPY_SRC)

        bind_group = self.device.create_bind_group(
            layout=self.trace_pipeline.get_bind_group_layout(0),
            entries=[
                {"binding": 0, "resource": {"buffer": p_buf, "offset": 0, "size": p_buf.size}},
                {"binding": 1, "resource": {"buffer": h_buf, "offset": 0, "size": h_buf.size}},
                {"binding": 2, "resource": {"buffer": a_buf, "offset": 0, "size": a_buf.size}},
                {"binding": 3, "resource": {"buffer": z_buf, "offset": 0, "size": z_buf.size}},
            ]
        )

        enc = self.device.create_command_encoder()
        cp = enc.begin_compute_pass()
        cp.set_pipeline(self.trace_pipeline)
        cp.set_bind_group(0, bind_group)
        cp.dispatch_workgroups((N * K + 63) // 64, 1, 1)
        cp.end()

        self.device.queue.submit([enc.finish()])
        out = np.frombuffer(self.device.queue.read_buffer(z_buf), dtype=np.float32).reshape(N, K)
        return out

    def run_recurrent_step(self, W: np.ndarray, h: np.ndarray, b: np.ndarray, x: np.ndarray) -> np.ndarray:
        N = len(h)
        params = np.array([N, 0, 0, 0], dtype=np.uint32)
        p_buf = self.device.create_buffer_with_data(data=params, usage=wgpu.BufferUsage.UNIFORM)
        w_buf = self.device.create_buffer_with_data(data=W.astype(np.float32), usage=wgpu.BufferUsage.STORAGE)
        h_buf = self.device.create_buffer_with_data(data=h.astype(np.float32), usage=wgpu.BufferUsage.STORAGE)
        b_buf = self.device.create_buffer_with_data(data=b.astype(np.float32), usage=wgpu.BufferUsage.STORAGE)
        x_buf = self.device.create_buffer_with_data(data=x.astype(np.float32), usage=wgpu.BufferUsage.STORAGE)
        hn_buf = self.device.create_buffer(size=N * 4, usage=wgpu.BufferUsage.STORAGE | wgpu.BufferUsage.COPY_SRC)

        bind_group = self.device.create_bind_group(
            layout=self.recurrent_pipeline.get_bind_group_layout(0),
            entries=[
                {"binding": 0, "resource": {"buffer": p_buf, "offset": 0, "size": p_buf.size}},
                {"binding": 1, "resource": {"buffer": w_buf, "offset": 0, "size": w_buf.size}},
                {"binding": 2, "resource": {"buffer": h_buf, "offset": 0, "size": h_buf.size}},
                {"binding": 3, "resource": {"buffer": b_buf, "offset": 0, "size": b_buf.size}},
                {"binding": 4, "resource": {"buffer": x_buf, "offset": 0, "size": x_buf.size}},
                {"binding": 5, "resource": {"buffer": hn_buf, "offset": 0, "size": hn_buf.size}},
            ]
        )

        enc = self.device.create_command_encoder()
        cp = enc.begin_compute_pass()
        cp.set_pipeline(self.recurrent_pipeline)
        cp.set_bind_group(0, bind_group)
        cp.dispatch_workgroups((N + 63) // 64, 1, 1)
        cp.end()

        self.device.queue.submit([enc.finish()])
        out = np.frombuffer(self.device.queue.read_buffer(hn_buf), dtype=np.float32)
        return out

    def run_sparse_scatter(self, src: np.ndarray, dst: np.ndarray, weights: np.ndarray, h_in: np.ndarray, num_dst: int) -> np.ndarray:
        num_edges = len(src)
        params = np.array([num_edges, 0, 0, 0], dtype=np.uint32)
        p_buf = self.device.create_buffer_with_data(data=params, usage=wgpu.BufferUsage.UNIFORM)
        src_buf = self.device.create_buffer_with_data(data=src.astype(np.uint32), usage=wgpu.BufferUsage.STORAGE)
        dst_buf = self.device.create_buffer_with_data(data=dst.astype(np.uint32), usage=wgpu.BufferUsage.STORAGE)
        w_buf = self.device.create_buffer_with_data(data=weights.astype(np.float32), usage=wgpu.BufferUsage.STORAGE)
        h_buf = self.device.create_buffer_with_data(data=h_in.astype(np.float32), usage=wgpu.BufferUsage.STORAGE)

        # Zero-initialized destination buffer
        h_out_zeros = np.zeros(num_dst, dtype=np.int32)
        out_buf = self.device.create_buffer_with_data(data=h_out_zeros, usage=wgpu.BufferUsage.STORAGE | wgpu.BufferUsage.COPY_SRC)

        bind_group = self.device.create_bind_group(
            layout=self.sparse_scatter_pipeline.get_bind_group_layout(0),
            entries=[
                {"binding": 0, "resource": {"buffer": p_buf, "offset": 0, "size": p_buf.size}},
                {"binding": 1, "resource": {"buffer": src_buf, "offset": 0, "size": src_buf.size}},
                {"binding": 2, "resource": {"buffer": dst_buf, "offset": 0, "size": dst_buf.size}},
                {"binding": 3, "resource": {"buffer": w_buf, "offset": 0, "size": w_buf.size}},
                {"binding": 4, "resource": {"buffer": h_buf, "offset": 0, "size": h_buf.size}},
                {"binding": 5, "resource": {"buffer": out_buf, "offset": 0, "size": out_buf.size}},
            ]
        )

        enc = self.device.create_command_encoder()
        cp = enc.begin_compute_pass()
        cp.set_pipeline(self.sparse_scatter_pipeline)
        cp.set_bind_group(0, bind_group)
        cp.dispatch_workgroups((num_edges + 63) // 64, 1, 1)
        cp.end()

        self.device.queue.submit([enc.finish()])
        raw_out = np.frombuffer(self.device.queue.read_buffer(out_buf), dtype=np.int32)
        # Convert back from fixed point
        return raw_out.astype(np.float32) / 10000.0
