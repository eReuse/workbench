#!/bin/sh -eu

set -x
set -e

# inspired from Ander in https://code.ungleich.ch/ungleich-public/cdist/issues/4
# this is a way to reuse a function used inside and outside of chroot
# this function is used both in shell and chroot
decide_if_update_str="$(cat <<END
decide_if_update() {
  if [ ! -d /var/lib/apt/lists ] \
    || [ -n "\$( find /etc/apt -newer /var/lib/apt/lists )" ] \
    || [ ! -f /var/cache/apt/pkgcache.bin ] \
    || [ "\$( stat --format %Y /var/cache/apt/pkgcache.bin )" -lt "\$( date +%s -d '-1 day' )" ]
  then
    if [ -d /var/lib/apt/lists ]; then
      \${SUDO} touch /var/lib/apt/lists
    fi
    apt_opts="-o Acquire::AllowReleaseInfoChange::Suite=true -o Acquire::AllowReleaseInfoChange::Version=true"
    # apt update could have problems such as key expirations, proceed anyway
    \${SUDO} apt-get "\${apt_opts}" update || true
  fi
}
END
)"

create_iso() {
  # Copy kernel and initramfs
  ${SUDO} cp ${WB_PATH}/chroot/boot/vmlinuz-* ${WB_PATH}/staging/live/vmlinuz
  ${SUDO} cp ${WB_PATH}/chroot/boot/initrd.img-* ${WB_PATH}/staging/live/initrd
  # Creating ISO
  wbiso_path="${WB_PATH}/${wbiso_name}.iso"

  case "${BOOT_TYPE}" in
    isolinux)
      # 0x14 is FAT16 Hidden FAT16 <32, this is the only format detected in windows10 automatically when using a persistent volume of 10 MB
      ${SUDO} xorrisofs \
        -verbose \
        -iso-level 3 \
        -o "${wbiso_path}" \
        -full-iso9660-filenames \
        -volid "${wbiso_name}" \
        -isohybrid-mbr /usr/lib/ISOLINUX/isohdpfx.bin \
        -eltorito-boot \
          isolinux/isolinux.bin \
          -no-emul-boot \
          -boot-load-size 4 \
          -boot-info-table \
          --eltorito-catalog isolinux/isolinux.cat \
        -eltorito-alt-boot \
          -e /EFI/boot/efiboot.img \
          -no-emul-boot \
          -isohybrid-gpt-basdat \
        -append_partition 2 0xef ${WB_PATH}/staging/EFI/boot/efiboot.img \
        -append_partition 3 0x14 "${rw_img_path}" \
        "${WB_PATH}/staging"
    ;;
    grub)
      # thanks https://github.com/ventoy/Ventoy/blob/master/LiveCD/livecd.sh#L80
      # extra src https://willhaley.com/blog/custom-debian-live-environment/
      ${SUDO} xorriso \
        -o "${wbiso_path}" \
        -volid "${wbiso_name}" \
        -as mkisofs \
        -allow-lowercase \
        --sort-weight 0 / \
        --sort-weight 1 /EFI \
        -verbose \
        -rock \
        -joliet \
        -publisher 'VENTOY COMPATIBLE' \
        -preparer 'https://www.ventoy.net' \
        -sysid 'Ventoy' \
        -appid 'VentoyLiveCD' \
        --grub2-boot-info \
        --grub2-mbr /usr/lib/ ../GRUB/boot_hybrid.img \
#        --grub2-mbr ../GRUB/boot_hybrid.img \
        -eltorito-boot \
          EFI/boot/cdrom.img \
          -no-emul-boot \
          -boot-load-size 4 \
          -boot-info-table \
          -eltorito-catalog EFI/boot/boot.cat \
        -eltorito-alt-boot \
          -e EFI/boot/efi.img \
          -no-emul-boot \
        -append_partition 2 0xEF EFI/boot/efi.img \
        -append_partition 3 0x14 "${rw_img_path}"
    ;;
    *)
      echo 'ERROR: create_iso wants an argument: isolinux or grub'
      exit 1
      ;;
  esac

  printf "\n\n  Image generated in build/${wbiso_path}\n\n"
}

isolinux_boot() {
  # TODO check next comment
  # we don't need to ensure grub is disabled because isolinux has preference
  isolinuxcfg_str="$(cat <<END
UI vesamenu.c32

MENU TITLE Boot Menu
DEFAULT linux
TIMEOUT 10
MENU RESOLUTION 640 480
MENU COLOR border       30;44   #40ffffff #a0000000 std
MENU COLOR title        1;36;44 #9033ccff #a0000000 std
MENU COLOR sel          7;37;40 #e0ffffff #20ffffff all
MENU COLOR unsel        37;44   #50ffffff #a0000000 std
MENU COLOR help         37;40   #c0ffffff #a0000000 std
MENU COLOR timeout_msg  37;40   #80ffffff #00000000 std
MENU COLOR timeout      1;37;40 #c0ffffff #00000000 std
MENU COLOR msg07        37;40   #90ffffff #a0000000 std
MENU COLOR tabmsg       31;40   #30ffffff #00000000 std

# TODO check next comment
# THIS IS WHAT IS RUNNING NOW! (isolinux)
# disabled predicted names -> src https://michlstechblog.info/blog/linux-disable-assignment-of-new-names-for-network-interfaces/
LABEL linux
  MENU LABEL Debian Live [BIOS/ISOLINUX]
  MENU DEFAULT
  KERNEL /live/vmlinuz
  APPEND initrd=/live/initrd boot=live net.ifnames=0 biosdevname=0 persistence

LABEL linux
  MENU LABEL Debian Live [BIOS/ISOLINUX] (nomodeset)
  MENU DEFAULT
  KERNEL /live/vmlinuz
  APPEND initrd=/live/initrd boot=live nomodeset
END
)"
  #   TIMEOUT 60 means 6 seconds :)
  sudo tee "${WB_PATH}/staging/isolinux/isolinux.cfg" <<EOF
${isolinuxcfg_str}
EOF
  ${SUDO} cp /usr/lib/ISOLINUX/isolinux.bin "${WB_PATH}/staging/isolinux/"
  ${SUDO} cp /usr/lib/syslinux/modules/bios/* "${WB_PATH}/staging/isolinux/"
}

grub_boot() {
  # TODO check next removal
  # ensure isolinux is disabled
  #rm -f "${WB_PATH}/staging/isolinux/isolinux.cfg"
  #rm -f "${WB_PATH}/staging/isolinux/isolinux.bin"

  grubcfg_str="$(cat <<END
search --set=root --file /${wbiso_name}

set default="0"
set timeout=1

# If X has issues finding screens, experiment with/without nomodeset.

menuentry "Debian Live [EFI/GRUB]" {
    linux (\$root)/live/vmlinuz boot=live
    initrd (\$root)/live/initrd
}

menuentry "Debian Live [EFI/GRUB] (nomodeset)" {
    linux (\$root)/live/vmlinuz boot=live nomodeset
    initrd (\$root)/live/initrd
}
END
)"
  ${SUDO} tee "${WB_PATH}/staging/boot/grub/grub.cfg" <<EOF
${grubcfg_str}
EOF

  ${SUDO} tee "${WB_PATH}/tmp/grub-standalone.cfg" <<EOF
search --set=root --file /${wbiso_name}
set prefix=(\$root)/boot/grub/
configfile /boot/grub/grub.cfg
EOF
  ${SUDO} cp -r /usr/lib/grub/x86_64-efi/* "${WB_PATH}/staging/boot/grub/x86_64-efi/"

  ${SUDO} grub-mkstandalone \
    --format=x86_64-efi \
    --output=${WB_PATH}/tmp/bootx64.efi \
    --locales="" \
    --fonts="" \
    "boot/grub/grub.cfg=${WB_PATH}/tmp/grub-standalone.cfg"

  # prepare uefi secureboot files
  #   bootx64 is the filename is looking to boot, and we force it to be the shimx64 file for uefi secureboot
  #   shimx64 redirects to grubx64 -> src https://askubuntu.com/questions/874584/how-does-secure-boot-actually-work
  #   grubx64 looks for a file in /EFI/debian/grub.cfg -> src src https://unix.stackexchange.com/questions/648089/uefi-grub-not-finding-config-file
  ${SUDO} cp /usr/lib/shim/shimx64.efi.signed /tmp/bootx64.efi
  ${SUDO} cp /usr/lib/grub/x86_64-efi-signed/grubx64.efi.signed /tmp/grubx64.efi
  ${SUDO} cp ${WB_PATH}/tmp/grub-standalone.cfg ${WB_PATH}/staging/EFI/debian/grub.cfg

  (
    cd ${WB_PATH}/staging/EFI/boot
      ${SUDO} dd if=/dev/zero of=efiboot.img bs=1M count=20
      ${SUDO} mkfs.vfat efiboot.img
      ${SUDO} mmd -i efiboot.img efi efi/boot
      ${SUDO} mcopy -vi efiboot.img \
        /tmp/bootx64.efi \
        /tmp/grubx64.efi \
          ::efi/boot/
  )
}

create_boot_system() {
  case "${BOOT_TYPE}" in
    isolinux)
      isolinux_boot
      grub_boot
    ;;
    grub)
      grub_boot
    ;;
    *)
      echo 'ERROR: create_boot_system wants an argument: isolinux or grub'
      exit 1
      ;;
  esac
}

compress_chroot_dir() {
  # Faster squashfs when debugging -> src https://forums.fedoraforum.org/showthread.php?284366-squashfs-wo-compression-speed-up
  if [ "${DEBUG:-}" ]; then
    DEBUG_SQUASHFS_ARGS='-noI -noD -noF -noX'
  fi

  # why squashfs -> https://unix.stackexchange.com/questions/163190/why-do-liveusbs-use-squashfs-and-similar-file-systems
  # noappend option needed to avoid this situation -> https://unix.stackexchange.com/questions/80447/merging-preexisting-source-folders-in-mksquashfs
  ${SUDO} mksquashfs \
    ${WB_PATH}/chroot \
    ${WB_PATH}/staging/live/filesystem.squashfs \
    ${DEBUG_SQUASHFS_ARGS:-} \
    -noappend -e boot
}


create_persistence_partition() {
  # persistent partition
  rw_img_name="wbp_vfat.img"
  rw_img_path="${WB_PATH}/staging/${rw_img_name}"
  if [ ! -f "${rw_img_path}" ] || [ "${DEBUG:-}" ]; then
    ${SUDO} dd if=/dev/zero of="${rw_img_path}" bs=10M count=1
    ${SUDO} mkfs.vfat "${rw_img_path}"

    # generate structure on persistent partition
    tmp_rw_mount="/mnt/${rw_img_name}"
    ${SUDO} umount -f -l "${tmp_rw_mount}" >/dev/null 2>&1 || true
    mkdir -p "${tmp_rw_mount}"
    ${SUDO} mount "$(pwd)/${rw_img_path}" "${tmp_rw_mount}"
    ${SUDO} mkdir -p "${tmp_rw_mount}/wb_settings"
    ${SUDO} touch "${tmp_rw_mount}/wb_settings/settings.ini"
    ${SUDO} mkdir -p "${tmp_rw_mount}/wb_snapshots"
    ${SUDO} umount "${tmp_rw_mount}"

    uuid="$(blkid "${rw_img_path}" | awk '{ print $3; }')"
    # no fail on boot -> src https://askubuntu.com/questions/14365/mount-an-external-drive-at-boot-time-only-if-it-is-plugged-in/99628#99628
    # use tee instead of cat -> src https://stackoverflow.com/questions/2953081/how-can-i-write-a-heredoc-to-a-file-in-bash-script/17093489#17093489
    ${SUDO} tee "${WB_PATH}/chroot/etc/fstab" <<END
# next three lines originally appeared on fstab, we preserve them
# UNCONFIGURED FSTAB FOR BASE SYSTEM
overlay / overlay rw 0 0
tmpfs /tmp tmpfs nosuid,nodev 0 0
${uuid} /mnt vfat defaults,nofail 0 0
END
  fi
  # src https://manpages.debian.org/testing/open-infrastructure-system-boot/persistence.conf.5.en.html
  echo "/ union" | ${SUDO} tee "${WB_PATH}/chroot/persistence.conf"
}


chroot_netdns_conf_str="$(cat<<END
###################
# configure network
mkdir -p /etc/network/
cat > /etc/network/interfaces <<END2
auto lo
iface lo inet loopback

auto eth0
iface eth0 inet dhcp
END2

###################
# configure dns
cat > /etc/resolv.conf <<END2
nameserver 1.1.1.1
END2

###################
# configure hosts
cat > /etc/hosts <<END2
127.0.0.1    localhost \${hostname}
::1          localhost ip6-localhost ip6-loopback
ff02::1      ip6-allnodes
ff02::2      ip6-allrouters
END2
END
)"

run_chroot() {
  # non interactive chroot -> src https://stackoverflow.com/questions/51305706/shell-script-that-does-chroot-and-execute-commands-in-chroot
  # stop apt-get from greedily reading the stdin -> src https://askubuntu.com/questions/638686/apt-get-exits-bash-script-after-installing-packages/638754#638754
  ${SUDO} chroot ${WB_PATH}/chroot <<CHROOT
set -x
set -e

echo "${hostname}" > /etc/hostname

# check what linux images are available on the system
# Figure out which Linux Kernel you want in the live environment.
#   apt-cache search linux-image

backports_path="/etc/apt/sources.list.d/backports.list"
if [ ! -f "\${backports_path}" ]; then
  backports_repo='deb http://deb.debian.org/debian ${VERSION_CODENAME}-backports main contrib'
  printf "\${backports_repo}" > "\${backports_path}"
fi

# this env var confuses sudo detection
unset SUDO_USER
${detect_user_str}
detect_user

# Installing packages
${decide_if_update_str}
decide_if_update

apt-get install -y --no-install-recommends \
  linux-image-amd64 \
  live-boot \
  systemd-sysv

### START workbench_lite installation

echo 'Install Workbench'

# Install WB debian requirements
apt-get install -y --no-install-recommends \
  python3 python3-dev python3-pip \
  sysbench libusb-1.0-0 parted stress cifs-utils \
  dmidecode smartmontools hwinfo pciutils < /dev/null

# Install WB python requirements
pip3 install python-dateutil==2.8.2 hashids==1.3.1 requests~=2.21.0 python-decouple==3.3 colorama==0.4.1 click==7.0 ereuse-utils[cli,getter,session,usb_flash_drive]==0.4.0b49 inflection==0.3.1 ntplib==0.3.4 numpy==1.22.2 pint==0.9 pySMART.smartx==0.3.9 requests-toolbelt==0.9.1 tqdm==4.32.2

# Install lshw B02.19 utility using backports
apt install -y -t ${VERSION_CODENAME}-backports lshw  < /dev/null

#Install WB
pip3 install -e ./opt/workbench/

# Autologin root user
# src https://wiki.archlinux.org/title/getty#Automatic_login_to_virtual_console
mkdir -p /etc/systemd/system/getty@tty1.service.d/
cat > /etc/systemd/system/getty@tty1.service.d/override.conf <<END2
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin root --noclear %I \$TERM
END2

systemctl enable getty@tty1.service

### END workbench-live installation


# other debian utilities
apt-get install -y --no-install-recommends \
  iproute2 iputils-ping ifupdown isc-dhcp-client \
  fdisk parted \
  curl openssh-client \
  less \
  jq \
  nano vim-tiny \
  < /dev/null

${chroot_netdns_conf_str}

# Set up root user
#   this is the root password
#   Method3: Use echo
#     src https://www.systutorials.com/changing-linux-users-password-in-one-command-line/
#     TODO hardcoded password
printf 'workbench\nworkbench' | passwd root

# general cleanup if production image
if [ -z "${DEBUG:-}" ]; then
  apt-get clean < /dev/null
fi

CHROOT
}

prepare_chroot_env() {
  # version of debian the bootstrap is going to build
  #   if no VERSION_CODENAME is specified we assume that the bootstrap is going to
  #   be build with the same version of debian being executed because some files
  #   are copied from our root system
  if [ -z "${VERSION_CODENAME:-}" ]; then
    . /etc/os-release
    echo "TAKING OS-RELEASE FILE"
  fi

  chroot_path="${WB_PATH}/chroot"
  if [ ! -d "${chroot_path}" ]; then
    ${SUDO} debootstrap --arch=amd64 --variant=minbase ${VERSION_CODENAME} ${WB_PATH}/chroot http://deb.debian.org/debian/
    # TODO does this make sense?
    ${SUDO} chown -R "${USER}:" ${WB_PATH}/chroot
  fi

  wb_dir="${WB_PATH}/chroot/opt/workbench"
  mkdir -p "${wb_dir}"
  ${SUDO} cp -r ../ereuse_workbench "${wb_dir}"
  ${SUDO} cp ../setup.py "${wb_dir}"
  ${SUDO} cp ../README.rst "${wb_dir}"
  ${SUDO} cp ../examples/.profile "${WB_PATH}/chroot/root/"
}

# thanks https://willhaley.com/blog/custom-debian-live-environment/
install_requirements() {
  # Install requirements
  eval "${decide_if_update_str}" && decide_if_update
  image_deps='debootstrap
                squashfs-tools
                xorriso
                mtools'
  # secureboot:
  #   -> extra src https://wiki.debian.org/SecureBoot/
  #   -> extra src https://wiki.debian.org/SecureBoot/VirtualMachine
  #   -> extra src https://wiki.debian.org/GrubEFIReinstall
  bootloader_deps='isolinux
                     syslinux-efi
                     grub-pc-bin
                     grub-efi-amd64-bin
                     ovmf
                     grub-efi-amd64-signed'
  ${SUDO} apt-get install -y \
    ${image_deps} \
    ${bootloader_deps}
}

# thanks https://willhaley.com/blog/custom-debian-live-environment/
create_base_dirs() {
  mkdir -p ${WB_PATH}
  mkdir -p ${WB_PATH}/staging/EFI/boot
  mkdir -p ${WB_PATH}/staging/boot/grub/x86_64-efi
  mkdir -p ${WB_PATH}/staging/isolinux
  mkdir -p ${WB_PATH}/staging/live
  mkdir -p ${WB_PATH}/tmp
  # usb name
  ${SUDO} touch ${WB_PATH}/staging/${wbiso_name}

  # for uefi secure boot grub config file
  mkdir -p ${WB_PATH}/staging/EFI/debian
}

# this function is used both in shell and chroot
detect_user_str="$(cat <<END
detect_user() {
  userid="\$(id -u)"
  # detect non root user without sudo
  if [ ! "\${userid}" = 0 ] && id \${USER} | grep -qv sudo; then
    echo "ERROR: this script needs root or sudo permissions (current user is not part of sudo group)"
    exit 1
  # detect user with sudo or already on sudo src https://serverfault.com/questions/568627/can-a-program-tell-it-is-being-run-under-sudo/568628#568628
  elif [ ! "\${userid}" = 0 ] || [ -n "\${SUDO_USER}" ]; then
    SUDO='sudo'
    # TODO check
    # jump to current dir where the script is so relative links work
    cd "\$(dirname "\${0}")"
    # workbench working directory to build the iso
    WB_PATH="wbiso"
  # detect pure root
  elif [ "\${userid}" = 0 ]; then
    SUDO=''
    WB_PATH="/opt/workbench_live_dev"
  fi
}
END
)"

main() {

  if [ "${DEBUG:-}" ]; then
    WB_VERSION='debug'
  else
    WB_VERSION='14.0.0-beta'
  fi
  wbiso_name="USODY_${WB_VERSION}"
  hostname='workbench-live'

  eval "${detect_user_str}" && detect_user

  create_base_dirs

  install_requirements

  prepare_chroot_env

  run_chroot

  create_persistence_partition

  compress_chroot_dir

  # do not change boot_type, explore from isolinux boot_type to make it work on uefi
  # theoretically this approach is giving compatibility for all kinds of systems -> src https://willhaley.com/blog/custom-debian-live-environment/
  #   grub, right now, is not interesting to explore
  BOOT_TYPE='isolinux'

  create_boot_system

  create_iso

}

main "${@}"
