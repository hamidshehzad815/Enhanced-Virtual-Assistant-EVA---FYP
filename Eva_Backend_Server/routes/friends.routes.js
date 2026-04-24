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
  listBlockedUsers,
  searchUsers,
  respondToFriendRequest,
  blockFriend,
  unblockFriend,
  unfriend,
} = require("../controllers/friends.controller");

router.post("/request", protect, sendFriendRequest);
router.get("/", protect, listFriends);
router.get("/requests", protect, listFriendRequests);
router.get("/blocked", protect, listBlockedUsers);
router.get("/search", protect, searchUsers);
router.post("/block/:userId", protect, blockFriend);
router.post("/unblock/:userId", protect, unblockFriend);
router.delete("/:id", protect, unfriend);
router.patch("/:id/respond", protect, respondToFriendRequest);

module.exports = router;
