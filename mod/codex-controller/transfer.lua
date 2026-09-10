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
        local before=stack.count
        dst[j].transfer_stack(stack,math.min(left,before))
        local after=stack.valid_for_read and stack.count or 0
        left=left-(before-after)
      end
    end
    if left==0 then return count end
  end
  -- Keep any completed native transfer visible; never reconstruct items to
  -- conceal an unexpected partial outcome.
  error('transfer_incomplete')
end
return M
