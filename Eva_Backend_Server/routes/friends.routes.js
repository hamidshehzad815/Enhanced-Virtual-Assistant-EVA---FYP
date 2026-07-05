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
  searchUsers,
  respondToFriendRequest,
  unfriend,
} = require("../controllers/friends.controller");

router.post("/request", protect, sendFriendRequest);
router.get("/", protect, listFriends);
router.get("/requests", protect, listFriendRequests);
router.get("/search", protect, searchUsers);
router.delete("/:id", protect, unfriend);
router.patch("/:id/respond", protect, respondToFriendRequest);

module.exports = router;
