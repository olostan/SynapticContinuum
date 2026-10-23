#pragma once

#include "queue_interface.hpp"
#include "binary_heap.hpp"
#include <vector>
#include <cmath>
#include <stdexcept>
#include <algorithm>

namespace sc {

class BucketEventQueue : public IEventQueue {
public:
    explicit BucketEventQueue(double bucket_width = 0.2, size_t num_buckets = 64)
        : bucket_width_(bucket_width > 0.0 ? bucket_width : 0.2),
          num_buckets_(num_buckets > 0 ? num_buckets : 64),
          ring_(num_buckets_),
          current_bucket_idx_(0),
          base_time_(0.0) {}

    void push(const Event& event) override {
        total_size_++;
        if (total_size_ > peak_size_) {
            peak_size_ = total_size_;
        }

        if (event.timestamp < base_time_) {
            // Should not happen in causal event scheduling, but handle gracefully in current bucket
            ring_[current_bucket_idx_].push(event);
            return;
        }

        int64_t b_offset = static_cast<int64_t>((event.timestamp - base_time_) / bucket_width_);
        if (b_offset < static_cast<int64_t>(num_buckets_)) {
            size_t slot = (current_bucket_idx_ + static_cast<size_t>(b_offset)) % num_buckets_;
            ring_[slot].push(event);
        } else {
            overflow_heap_.push(event);
        }
    }

    Event pop() override {
        advance_to_next_available();
        if (total_size_ == 0) {
            throw std::runtime_error("pop from empty BucketEventQueue");
        }

        total_size_--;

        // Check if current bucket has events
        if (!ring_[current_bucket_idx_].empty()) {
            return ring_[current_bucket_idx_].pop();
        }

        // Fallback to overflow
        if (!overflow_heap_.empty()) {
            return overflow_heap_.pop();
        }

        throw std::runtime_error("Inconsistent state in BucketEventQueue");
    }

    const Event& peek() const override {
        const_cast<BucketEventQueue*>(this)->advance_to_next_available();
        if (total_size_ == 0) {
            throw std::runtime_error("peek from empty BucketEventQueue");
        }
        if (!ring_[current_bucket_idx_].empty()) {
            return ring_[current_bucket_idx_].peek();
        }
        if (!overflow_heap_.empty()) {
            return overflow_heap_.peek();
        }
        throw std::runtime_error("Inconsistent state in BucketEventQueue::peek");
    }

    bool empty() const noexcept override {
        return total_size_ == 0;
    }

    size_t size() const noexcept override {
        return total_size_;
    }

    size_t peak_size() const noexcept override {
        return peak_size_;
    }

    void clear() override {
        for (auto& q : ring_) {
            q.clear();
        }
        overflow_heap_.clear();
        current_bucket_idx_ = 0;
        base_time_ = 0.0;
        total_size_ = 0;
        peak_size_ = 0;
    }

    size_t memory_bytes() const noexcept override {
        size_t b = ring_.capacity() * sizeof(BinaryHeapQueue);
        for (const auto& q : ring_) {
            b += q.memory_bytes();
        }
        b += overflow_heap_.memory_bytes();
        return b;
    }

private:
    double bucket_width_;
    size_t num_buckets_;
    std::vector<BinaryHeapQueue> ring_;
    BinaryHeapQueue overflow_heap_;
    size_t current_bucket_idx_;
    double base_time_;
    size_t total_size_ = 0;
    size_t peak_size_ = 0;

    void advance_to_next_available() {
        if (total_size_ == 0) return;

        while (ring_[current_bucket_idx_].empty()) {
            // Check if overflow has an event that is earlier than moving forward
            if (!overflow_heap_.empty() && ring_is_all_empty()) {
                double next_overflow_t = overflow_heap_.peek().timestamp;
                // Fast-forward base_time to near next overflow event
                int64_t jump = static_cast<int64_t>((next_overflow_t - base_time_) / bucket_width_);
                if (jump > 0) {
                    base_time_ += jump * bucket_width_;
                    current_bucket_idx_ = (current_bucket_idx_ + static_cast<size_t>(jump % num_buckets_)) % num_buckets_;
                }
            }

            // Transfer qualifying events from overflow into ring
            while (!overflow_heap_.empty()) {
                const Event& ev = overflow_heap_.peek();
                int64_t b_offset = static_cast<int64_t>((ev.timestamp - base_time_) / bucket_width_);
                if (b_offset < 0) {
                    ring_[current_bucket_idx_].push(overflow_heap_.pop());
                } else if (b_offset < static_cast<int64_t>(num_buckets_)) {
                    size_t slot = (current_bucket_idx_ + static_cast<size_t>(b_offset)) % num_buckets_;
                    ring_[slot].push(overflow_heap_.pop());
                } else {
                    break;
                }
            }

            if (!ring_[current_bucket_idx_].empty() || total_size_ == 0) {
                break;
            }

            // Advance by one bucket
            current_bucket_idx_ = (current_bucket_idx_ + 1) % num_buckets_;
            base_time_ += bucket_width_;

            // If we wrapped all the way and overflow is also empty, stop
            if (ring_is_all_empty() && overflow_heap_.empty()) {
                break;
            }
        }
    }

    bool ring_is_all_empty() const noexcept {
        for (const auto& q : ring_) {
            if (!q.empty()) return false;
        }
        return true;
    }
};

} // namespace sc
