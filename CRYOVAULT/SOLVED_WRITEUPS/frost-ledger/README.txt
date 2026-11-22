Bay 07 controller — offline registry export
===========================================

The cabinet that held bay 07's controller went down with the vault and its
vendor reader went with it. What survived is the registry volume itself, the
documentation that happened to be on the controller image, and fvrctl.

We need the bay's thaw-authority record:

    bay/07/thaw-authority

The record's authority-token is what the recovery team needs.

Contents:
  registry.fvr                          the registry volume
  usr/sbin/fvrctl                       the shipped control utility
  usr/share/doc/fvregd/ONDISK-NOTES.txt on-disk format notes
  usr/share/doc/fvregd/RELEASE-NOTES.txt   changelog
  include/fvr_format.h                  platform SDK header
  var/log/fvregd.log                    the controller's last log

Flag format: isfcr{...}
