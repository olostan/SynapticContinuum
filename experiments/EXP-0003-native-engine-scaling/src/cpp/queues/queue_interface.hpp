#pragma once

#include "../core/types.hpp"
#include <cstdint>

namespace sc {

class IEventQueue {
public:
    virtual ~IEventQueue() = default;

    virtual void push(const Event& event) = 0;
    virtual Event pop() = 0;
    virtual const Event& peek() const = 0;
    virtual bool empty() const noexcept = 0;
    virtual size_t size() const noexcept = 0;
    virtual size_t peak_size() const noexcept = 0;
    virtual void clear() = 0;
    virtual size_t memory_bytes() const noexcept = 0;
};

} // namespace sc
