#pragma once

#include "queue_interface.hpp"
#include <vector>
#include <stdexcept>
#include <algorithm>

namespace sc {

class BinaryHeapQueue : public IEventQueue {
public:
    explicit BinaryHeapQueue(size_t reserve_capacity = 65536) {
        data_.reserve(reserve_capacity);
    }

    void push(const Event& event) override {
        data_.push_back(event);
        sift_up(data_.size() - 1);
        if (data_.size() > peak_size_) {
            peak_size_ = data_.size();
        }
    }

    Event pop() override {
        if (data_.empty()) {
            throw std::runtime_error("pop from empty BinaryHeapQueue");
        }
        Event top = data_[0];
        data_[0] = data_.back();
        data_.pop_back();
        if (!data_.empty()) {
            sift_down(0);
        }
        return top;
    }

    const Event& peek() const override {
        if (data_.empty()) {
            throw std::runtime_error("peek from empty BinaryHeapQueue");
        }
        return data_[0];
    }

    bool empty() const noexcept override {
        return data_.empty();
    }

    size_t size() const noexcept override {
        return data_.size();
    }

    size_t peak_size() const noexcept override {
        return peak_size_;
    }

    void clear() override {
        data_.clear();
        peak_size_ = 0;
    }

    size_t memory_bytes() const noexcept override {
        return data_.capacity() * sizeof(Event);
    }

private:
    std::vector<Event> data_;
    size_t peak_size_ = 0;

    void sift_up(size_t idx) {
        while (idx > 0) {
            size_t parent = (idx - 1) / 2;
            if (data_[idx] < data_[parent]) {
                std::swap(data_[idx], data_[parent]);
                idx = parent;
            } else {
                break;
            }
        }
    }

    void sift_down(size_t idx) {
        size_t n = data_.size();
        while (true) {
            size_t left = 2 * idx + 1;
            size_t right = 2 * idx + 2;
            size_t smallest = idx;

            if (left < n && data_[left] < data_[smallest]) {
                smallest = left;
            }
            if (right < n && data_[right] < data_[smallest]) {
                smallest = right;
            }
            if (smallest != idx) {
                std::swap(data_[idx], data_[smallest]);
                idx = smallest;
            } else {
                break;
            }
        }
    }
};

} // namespace sc
