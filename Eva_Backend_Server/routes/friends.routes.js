/**
 * Friends Routes
 */

const express = require("express");
const router = express.Router();

const { protect } = require("../middleware/auth");
const {
  sendFriendRequest,
  listFriends,
  listFriendRequests,
  respondToFriendRequest,
  blockFriend,
  unfriend,
} = require("../controllers/friends.controller");

router.post("/request", protect, sendFriendRequest);
router.get("/", protect, listFriends);
router.get("/requests", protect, listFriendRequests);
router.delete("/:id", protect, unfriend);
router.patch("/:id/respond", protect, respondToFriendRequest);
router.post("/:id/block", protect, blockFriend);

module.exports = router;
