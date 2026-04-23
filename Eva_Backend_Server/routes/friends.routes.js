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
} = require("../controllers/friends.controller");

router.post("/request", protect, sendFriendRequest);
router.get("/", protect, listFriends);
router.get("/requests", protect, listFriendRequests);
router.patch("/:id/respond", protect, respondToFriendRequest);
router.post("/:id/block", protect, blockFriend);

module.exports = router;
