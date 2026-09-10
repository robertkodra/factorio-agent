-- Transfer real stacks with the engine's amount-limited stack operation. This
-- preserves partial magazines, durability, quality and other stack metadata.
local M={}
function M.move(src,dst,item,count)
  if src==dst then error('same_inventory_transfer') end
  if src.get_item_count(item)<count then error('insufficient_items') end
  if dst.get_insertable_count(item)<count then error('insufficient_space') end
  local left=count
  for i=1,#src do
    local stack=src[i]
    if stack.valid_for_read and stack.name==item then
      for j=1,#dst do
        if not stack.valid_for_read or left==0 then break end
        local requested=math.min(left,stack.count)
        local before=src.get_item_count(item)
        local complete=dst[j].transfer_stack(stack,requested)
        -- Used tools/science can merge durability, changing physical stack
        -- counts by more than the requested amount. The native boolean reports
        -- whether the requested amount was transferred. Never infer a negative
        -- next request from that consolidation or from inventory auto-sorting.
        if complete then
          left=left-requested
        else
          local moved=before-src.get_item_count(item)
          if moved<0 or moved>requested then error('transfer_outcome_requires_reconciliation') end
          left=left-moved
        end
      end
    end
    if left==0 then return count end
  end
  -- Keep any completed native transfer visible; never reconstruct items to
  -- conceal an unexpected partial outcome.
  error('transfer_incomplete')
end
return M
