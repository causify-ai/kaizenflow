OPTS="--home-dir /home"

# Mac user.
useradd -u 501 $OPTS user_501
usermod -aG docker user_501

# Linux users.
# We start from id=1001, the upper bound can be changed if needed.
for current_linux_id in {1001..1050}
do
  useradd -u $current_linux_id $OPTS user_$current_linux_id
  usermod -aG docker user_$current_linux_id
done

sudo chmod -R 777 /home

# Allow users to access /mnt/tmpfs.
# TODO(gp): We could change the permissions in fstab.
sudo chmod 777 /mnt
